import pytest
from apps.ops.optimizer.simulator import simulate_ab_bootstrap

pytestmark = [pytest.mark.gate_ops]


def test_bootstrap_outputs_ci_fields():
    """부트스트랩 CI 필드 출력 확인"""
    hist = {
        "infra": {"incidents": [2, 3, 4], "cost": [1.0, 1.1]},
        "perf": {"incidents": [1, 1, 2], "cost": [0.2, 0.3]}
    }
    base = {"infra": 1.0, "perf": 1.0}
    cand = {"infra": 1.2, "perf": 0.9}
    rep = simulate_ab_bootstrap(hist, base, cand, traffic_split=0.5, iters=100, seed=7)

    for k in ("baseline", "candidate", "delta", "bootstrap"):
        assert k in rep
    for k in ("mean", "var", "ci95_low", "ci95_high"):
        assert k in rep["delta"]
    assert 0.0 <= rep["delta"]["p_win"] <= 1.0


def test_bootstrap_p_win_calculation():
    """p_win 계산 확인"""
    hist = {
        "infra": {"incidents": [2, 3], "cost": [1.0, 1.1]},
        "perf": {"incidents": [1, 2], "cost": [0.2, 0.3]}
    }
    base = {"infra": 1.0, "perf": 1.0}
    # candidate가 더 나쁜 경우
    cand = {"infra": 0.5, "perf": 0.5}
    rep = simulate_ab_bootstrap(hist, base, cand, iters=50, seed=42)

    # p_win이 0~1 범위인지 확인
    assert isinstance(rep["delta"]["p_win"], float)
    assert 0.0 <= rep["delta"]["p_win"] <= 1.0


def test_bootstrap_variance_calculation():
    """분산 계산 확인"""
    hist = {
        "infra": {"incidents": [2, 3, 4, 2, 3], "cost": [1.0, 1.1, 0.9, 1.0, 1.1]}
    }
    base = {"infra": 1.0}
    cand = {"infra": 1.2}
    rep = simulate_ab_bootstrap(hist, base, cand, iters=200, seed=11)

    assert "var" in rep["delta"]
    assert rep["delta"]["var"] >= 0.0
    assert "ci95_low" in rep["delta"]
    assert "ci95_high" in rep["delta"]
    # CI 범위가 mean을 포함하는지 확인
    mean = rep["delta"]["mean"]
    assert rep["delta"]["ci95_low"] <= mean <= rep["delta"]["ci95_high"]
