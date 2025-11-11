import pytest
from apps.ops.optimizer.calibration import compute_gain, apply_calibration_to_ab_report

pytestmark = [pytest.mark.gate_ops]


def test_compute_gain_basic():
    """기본 gain 계산"""
    pred = [1.0, 1.0, 1.0]
    obs = [0.5, 1.0, 1.5]  # 평균비 ≈ 1.0, slope ≈ 1.0 → gain≈1.0
    res = compute_gain(pred, obs)
    assert 0.8 <= res["gain"] <= 1.2
    assert res["samples"] == 3
    assert "method" in res


def test_apply_calibration():
    """AB 리포트에 교정치 적용"""
    ab = {"delta": {"mean": 1.0, "ci95_low": 0.5, "ci95_high": 1.5}}
    res = compute_gain([1.0], [0.8])
    out = apply_calibration_to_ab_report(ab, res["gain"])
    assert "calibrated_gain" in out["delta"]
    assert out["delta"]["mean"] == pytest.approx(1.0 * res["gain"], rel=0.01)


def test_compute_gain_empty():
    """빈 데이터 처리"""
    res = compute_gain([], [])
    assert res["gain"] == 1.0
    assert res["samples"] == 0
    assert res["method"] == "identity"


def test_compute_gain_clipping():
    """극단값 클리핑"""
    # 매우 큰 비율
    res = compute_gain([1.0], [100.0])
    assert res["gain"] <= 10.0
    # 매우 작은 비율
    res2 = compute_gain([1.0], [0.01])
    assert res2["gain"] >= 0.1


def test_apply_calibration_objective():
    """objective 필드 교정"""
    ab = {"delta": {"objective": 2.0, "risk": 1.0}}
    out = apply_calibration_to_ab_report(ab, 0.5)
    assert out["delta"]["objective"] == 1.0
    assert out["delta"]["calibrated_gain"] == 0.5
