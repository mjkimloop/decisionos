import pytest
from apps.ops.optimizer.bayesian import update_pwin_beta, wilson_ci

pytestmark = [pytest.mark.gate_ops]


def test_beta_update_wilson():
    """베이지안 업데이트 + Wilson CI"""
    post = update_pwin_beta(2.0, 2.0, wins=7, trials=10)
    assert post["posterior"]["mean"] > 0.5
    assert 0.0 <= post["posterior"]["ci90_low"] <= post["posterior"]["ci90_high"] <= 1.0
    assert post["observed"]["wins"] == 7
    assert post["observed"]["trials"] == 10


def test_beta_update_prior():
    """사전분포 반영"""
    # 약한 사전 + 강한 관측
    post = update_pwin_beta(1.0, 1.0, wins=9, trials=10)
    # 사후 평균은 (1+9)/(1+9+1+1) = 10/12 ≈ 0.83
    assert 0.7 <= post["posterior"]["mean"] <= 0.9
    assert post["posterior"]["alpha"] == 10.0
    assert post["posterior"]["beta"] == 2.0


def test_wilson_ci_edge_cases():
    """Wilson CI 경계 케이스"""
    # n=0
    ci = wilson_ci(0, 0)
    assert ci == (0.0, 1.0)
    # 완벽한 성공
    ci = wilson_ci(10, 10)
    assert ci[0] > 0.5
    assert ci[1] == 1.0
    # 완벽한 실패
    ci = wilson_ci(0, 10)
    assert ci[0] == 0.0
    assert ci[1] < 0.5


def test_beta_update_no_trials():
    """관측 없는 경우"""
    post = update_pwin_beta(2.0, 2.0, wins=0, trials=0)
    # 사전분포만 유지
    assert post["posterior"]["alpha"] == 2.0
    assert post["posterior"]["beta"] == 2.0
    assert post["posterior"]["mean"] == 0.5
