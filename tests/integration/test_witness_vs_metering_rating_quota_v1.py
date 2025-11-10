"""
tests/integration/test_witness_vs_metering_rating_quota_v1.py

Integration smoke test: Witness CSV → Metering → Rating → Quota
v1 end-to-end verification (Gate-T + Gate-S).
"""
import io
import datetime as dt
import pytest

pytestmark = [pytest.mark.gate_t, pytest.mark.gate_s]

from apps.obs.witness.io import parse_witness_csv
from apps.metering.reconcile import aggregate_hourly_with_watermark
from apps.metering.watermark import WatermarkPolicy
from apps.rating.plans import Plan, MetricPlan
from apps.rating.engine import rate_report
from apps.limits.quota import QuotaRule, QuotaConfig, InMemoryQuotaState, apply_quota_batch

CSV = """\
tenant,metric,corr_id,ts,value
t1,tokens,req1,2025-01-01T10:15:00,50
t1,tokens,req2,2025-01-01T10:18:00,30
t1,tokens,req3,2025-01-01T10:20:00,50
t1,storage_gb,store1,2025-01-01T10:22:00,8
"""


def test_witness_to_metering_to_rating_to_quota():
    """
    Witness CSV 4건 → Metering 시간 집계 → Rating 요금 → Quota 한도 점검
    """
    # 1) Parse witness CSV
    evs = parse_witness_csv(io.StringIO(CSV))
    assert len(evs) == 4

    # 2) Aggregate hourly with watermark
    # Set now to 10:25 (within 15min of latest event at 10:20)
    now = dt.datetime(2025, 1, 1, 10, 25, 0)
    pol = WatermarkPolicy(max_lag_sec=900, drop_too_late=True)
    rep = aggregate_hourly_with_watermark(evs, now=now, policy=pol)
    # tokens: 50+30+50=130, storage_gb=8
    # 모두 on_time → late_dropped=0
    assert rep.counters.late_dropped == 0
    assert len(rep.buckets) == 2  # tokens, storage_gb
    tokens_bucket = next(b for b in rep.buckets.values() if b.metric == "tokens")
    assert tokens_bucket.sum == 130.0

    # 3) Rating: tokens included=100, overage_rate=0.02 → over=30 → 0.6
    #            storage_gb included=10, overage_rate=0.5 → over=0 → 0
    plan = Plan(
        name="Test",
        metrics={
            "tokens": MetricPlan(included=100.0, overage_rate=0.02),
            "storage_gb": MetricPlan(included=10.0, overage_rate=0.5),
        },
    )
    rating = rate_report(plan, rep)
    assert abs(rating.subtotal - 0.6) < 1e-6

    # 4) Quota: tokens soft=100, hard=120 → used=130 → deny (exceeds hard limit)
    qcfg = QuotaConfig(metrics={"tokens": QuotaRule(soft=100.0, hard=120.0)})
    qst = InMemoryQuotaState()
    deltas = {"tokens": 130.0}
    qres = apply_quota_batch("t1", deltas, qcfg, qst)
    tokens_decision = next(d for d in qres if d.metric == "tokens")
    assert tokens_decision.action == "deny"
    assert tokens_decision.used == 130.0

    # End-to-end: witness → metering → rating → quota verified.
