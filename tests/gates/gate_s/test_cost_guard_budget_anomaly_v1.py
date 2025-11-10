import pytest
pytestmark = [pytest.mark.gate_s]

from apps.cost_guard.budget import BudgetPolicy, check_budget
from apps.cost_guard.anomaly import EwmaConfig, ewma_detect

def test_budget_levels_and_ewma_spike():
    pol = BudgetPolicy(monthly_limit=100.0, warn_ratio=0.8)
    # 79 → ok, 85 → warn, 100 → exceeded
    assert check_budget(79.0, pol).level == "ok"
    assert check_budget(85.0, pol).level == "warn"
    assert check_budget(100.0, pol).level == "exceeded"

    # EWMA 스파이크: 마지막 값이 ewma*(1+ratio) 초과 → True
    cfg = EwmaConfig(alpha=0.3, spike_ratio=0.5)
    res = ewma_detect([10, 12, 11, 13, 40], cfg)
    assert res.is_spike is True
