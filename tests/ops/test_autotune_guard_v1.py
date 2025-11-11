import pytest
import os
import json

pytestmark = [pytest.mark.gate_ops]


def test_bounds_clamp():
    """Bounds 범위 제한"""
    from apps.ops.optimizer.guard import apply_bounds_slew

    proposed = {"delta_threshold": 0.25, "p_win_threshold": 0.40, "min_windows": 25}
    base = {"delta_threshold": 0.02, "p_win_threshold": 0.60, "min_windows": 5}
    bounds = {
        "delta_threshold_min": 0.01,
        "delta_threshold_max": 0.15,
        "p_win_threshold_min": 0.55,
        "p_win_threshold_max": 0.80,
        "min_windows_min": 3,
        "min_windows_max": 15
    }
    slew = {"delta_threshold": 0.10, "p_win_threshold": 0.10, "min_windows": 10}

    out = apply_bounds_slew(proposed, base, bounds, slew)

    # Bounds 체크
    assert 0.01 <= out["delta_threshold"] <= 0.15
    assert 0.55 <= out["p_win_threshold"] <= 0.80
    assert 3 <= out["min_windows"] <= 15


def test_slew_rate():
    """Slew-rate 변화량 제한"""
    from apps.ops.optimizer.guard import apply_bounds_slew

    proposed = {"delta_threshold": 0.10, "p_win_threshold": 0.75, "min_windows": 10}
    base = {"delta_threshold": 0.02, "p_win_threshold": 0.60, "min_windows": 5}
    bounds = {
        "delta_threshold_min": 0.01,
        "delta_threshold_max": 0.15,
        "p_win_threshold_min": 0.55,
        "p_win_threshold_max": 0.80,
        "min_windows_min": 3,
        "min_windows_max": 15
    }
    slew = {"delta_threshold": 0.02, "p_win_threshold": 0.05, "min_windows": 3}

    out = apply_bounds_slew(proposed, base, bounds, slew)

    # Slew-rate 체크 (부동소수점 허용오차 포함)
    assert abs(out["delta_threshold"] - base["delta_threshold"]) <= 0.02 + 1e-9
    assert abs(out["p_win_threshold"] - base["p_win_threshold"]) <= 0.05 + 1e-9
    assert abs(out["min_windows"] - base["min_windows"]) <= 3


def test_should_rollback(tmp_path):
    """롤백 판단 로직"""
    from apps.ops.optimizer.guard import should_rollback

    state_path = str(tmp_path / "consec.state")
    trigger = {"severity": ["critical"], "consecutive": 2}

    # 첫 번째 critical
    drift1 = {"severity": "critical", "abs_diff": 0.3, "kl": 2.0}
    rollback1 = should_rollback(drift1, trigger, state_path)
    assert not rollback1  # 아직 1회

    # 두 번째 연속 critical
    drift2 = {"severity": "critical", "abs_diff": 0.4, "kl": 2.5}
    rollback2 = should_rollback(drift2, trigger, state_path)
    assert rollback2  # 2회 연속 → 롤백

    # info로 리셋
    drift3 = {"severity": "info", "abs_diff": 0.01, "kl": 0.1}
    rollback3 = should_rollback(drift3, trigger, state_path)
    assert not rollback3

    # 다시 critical 1회
    drift4 = {"severity": "critical", "abs_diff": 0.3, "kl": 2.0}
    rollback4 = should_rollback(drift4, trigger, state_path)
    assert not rollback4
