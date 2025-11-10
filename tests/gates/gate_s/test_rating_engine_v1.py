import pytest
pytestmark = [pytest.mark.gate_s]

from apps.rating.plans import Plan, MetricPlan
from apps.rating.engine import rate_from_buckets
from apps.metering.schema import MeterBucket
import datetime as dt

def _bucket(metric, sumv):
    return MeterBucket(
        tenant="t1", metric=metric,
        window_start=dt.datetime(2025,1,1,10,0,0),
        window_end=dt.datetime(2025,1,1,11,0,0),
        count=1, sum=float(sumv), min=float(sumv), max=float(sumv)
    )

def test_rating_simple_overage():
    plan = Plan(name="Basic", metrics={
        "tokens": MetricPlan(included=100.0, overage_rate=0.02),
        "storage_gb": MetricPlan(included=10.0, overage_rate=0.5),
    })
    buckets = {
        "k1": _bucket("tokens", 150.0),      # over=50 → 1.0
        "k2": _bucket("storage_gb", 8.0),    # over=0 → 0
        "k3": _bucket("unknown", 5.0),       # not priced
    }
    res = rate_from_buckets(plan, buckets)
    assert abs(res.subtotal - 1.0) < 1e-6
    # unknown metric 라인 존재하며 과금 0
    assert any(i.metric == "unknown" and i.amount == 0.0 for i in res.items)
