import pytest
pytestmark = [pytest.mark.gate_s]

from apps.limits.quota import QuotaRule, QuotaConfig, InMemoryQuotaState, apply_quota_batch

def test_quota_soft_and_hard():
    cfg = QuotaConfig(metrics={"tokens": QuotaRule(soft=100.0, hard=120.0)})
    st = InMemoryQuotaState()
    # 누적 90 → allow
    d1 = apply_quota_batch("t1", {"tokens": 90.0}, cfg, st)[0]
    assert d1.action == "allow" and d1.used == 90.0
    # +20 → 110 → throttle
    d2 = apply_quota_batch("t1", {"tokens": 20.0}, cfg, st)[0]
    assert d2.action == "throttle" and d2.used == 110.0
    # +15 → 125 → deny
    d3 = apply_quota_batch("t1", {"tokens": 15.0}, cfg, st)[0]
    assert d3.action == "deny" and d3.used == 125.0
