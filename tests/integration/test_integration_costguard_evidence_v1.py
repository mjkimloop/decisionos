"""
tests/integration/test_integration_costguard_evidence_v1.py

통합 테스트: Witness → Metering → Rating/Quota → Cost-Guard → Evidence 스냅샷
전체 체인 실행 및 판정 근거 JSON 생성 검증.
"""
import io
import datetime as dt
import os
import json
import hashlib
import pytest

pytestmark = [pytest.mark.gate_t, pytest.mark.gate_s]

from apps.obs.witness.io import parse_witness_csv
from apps.metering.watermark import WatermarkPolicy
from apps.metering.reconcile import aggregate_hourly_with_watermark
from apps.rating.plans import Plan, MetricPlan
from apps.rating.engine import rate_report
from apps.limits.quota import QuotaRule, QuotaConfig, InMemoryQuotaState, apply_quota_batch
from apps.cost_guard.budget import BudgetPolicy, check_budget
from apps.cost_guard.anomaly import EwmaConfig, ewma_detect
from apps.obs.evidence.snapshot import build_snapshot, sha256_text

CSV = """\
tenant,metric,corr_id,ts,value
t1,tokens,c1,2025-01-01T10:30:00,60.0
t1,tokens,c2,2025-01-01T10:35:00,70.0
t1,storage_gb,c3,2025-01-01T10:32:00,8.0
"""


def test_costguard_evidence_snapshot(tmp_path):
    """
    Cost-Guard + Evidence 스냅샷 통합 테스트
    """
    # 1) Witness CSV 파싱
    csv_path = tmp_path / "witness.csv"
    csv_path.write_text(CSV, encoding="utf-8")

    with open(csv_path, "r", encoding="utf-8") as f:
        evs = parse_witness_csv(f)
    assert len(evs) == 3

    # 2) Metering 집계
    now = dt.datetime(2025, 1, 1, 10, 40, 0)
    pol = WatermarkPolicy(max_lag_sec=15 * 60, drop_too_late=True)
    rep = aggregate_hourly_with_watermark(evs, now=now, policy=pol)

    # 3) Rating 계산 (tokens: 130, storage_gb: 8)
    # tokens: included=100 → overage=30 → 30*0.02 = 0.6
    plan = Plan(
        name="Basic",
        metrics={
            "tokens": MetricPlan(included=100.0, overage_rate=0.02),
            "storage_gb": MetricPlan(included=10.0, overage_rate=0.50),
        },
    )
    rating = rate_report(plan, rep)
    assert abs(rating.subtotal - 0.6) < 1e-6

    # 4) Quota 점검 (tokens: deny, storage_gb: allow)
    qcfg = QuotaConfig(metrics={"tokens": QuotaRule(soft=100.0, hard=120.0)})
    qst = InMemoryQuotaState()
    deltas = {"tokens": 130.0, "storage_gb": 8.0}
    qres = list(apply_quota_batch("t1", deltas, qcfg, qst))
    q_actions = {d.metric: d.action for d in qres}
    assert q_actions["tokens"] == "deny"

    # 5) Cost-Guard 예산 점검 (0.6 > 0.5 → exceeded)
    budget = BudgetPolicy(monthly_limit=0.5, warn_ratio=0.8)
    bevt = check_budget(rating.subtotal, budget)
    assert bevt.level == "exceeded"

    # 6) Cost-Guard 이상 탐지 (급증 탐지: 0.6이 EWMA 대비 spike)
    ewma_cfg = EwmaConfig(alpha=0.3, spike_ratio=0.5)
    hist = [0.10, 0.12, 0.11, 0.13]  # 기준 히스토리
    anom = ewma_detect(hist + [rating.subtotal], ewma_cfg)
    assert anom.is_spike is True

    # 7) Evidence 스냅샷 생성
    csv_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    # buckets를 직렬화 가능한 형태로 변환
    buckets_serializable = {}
    for key, bucket in rep.buckets.items():
        buckets_serializable[key] = {
            "tenant": bucket.tenant,
            "metric": bucket.metric,
            "window_start": bucket.window_start.isoformat(),
            "window_end": bucket.window_end.isoformat(),
            "count": bucket.count,
            "sum": bucket.sum,
            "min": bucket.min,
            "max": bucket.max,
        }

    deltas_by_metric = {"tokens": 130.0, "storage_gb": 8.0}

    snap = build_snapshot(
        version="v0.5.11f",
        tenant="t1",
        witness_csv_path=str(csv_path),
        witness_rows=len(evs),
        witness_csv_sha256=csv_sha256,
        buckets=buckets_serializable,
        deltas_by_metric=deltas_by_metric,
        rating=rating,
        quota=qres,
        budget_level=bevt.level,
        budget_spent=rating.subtotal,
        budget_limit=budget.monthly_limit,
        anomaly_is_spike=anom.is_spike,
        anomaly_ewma=anom.ewma,
        anomaly_ratio=ewma_cfg.spike_ratio,
    )

    text = snap.to_json()
    data = json.loads(text)

    # 8) 필수 키 검사
    for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly", "integrity"]:
        assert k in data, f"Missing key: {k}"

    # 9) 예산/이상 판정 확인
    assert data["budget"]["level"] == "exceeded"
    assert data["anomaly"]["is_spike"] is True

    # 10) 무결성 서명 검증 (재계산)
    core = {
        k: data[k]
        for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]
    }
    recalc = sha256_text(json.dumps(core, ensure_ascii=False, sort_keys=True))
    assert recalc == data["integrity"]["signature_sha256"]

    # 11) 파일 저장 확인
    out = snap.save(dirpath=str(tmp_path))
    assert os.path.exists(out)

    # 저장된 파일 읽어서 재검증
    with open(out, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data["budget"]["level"] == "exceeded"
    assert saved_data["anomaly"]["is_spike"] is True
