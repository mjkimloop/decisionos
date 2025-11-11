"""
Test Adaptive Slew v1
적응형 cap 계산 및 autotune 통합 테스트
"""
import pytest
import json
import os
from apps.ops.optimizer.adaptive import (
    load_adaptive,
    load_bucket_stats,
    resolve_congestion,
    compute_adaptive_caps
)
from apps.ops.optimizer.guard import apply_bounds_slew_adaptive


def test_compute_adaptive_caps_variance_high():
    """분산 높을 때 cap 증가"""
    base_caps = {
        "delta_threshold": 0.02,
        "p_win_threshold": 0.05,
        "min_windows": 3
    }
    stats = {
        "variance": 0.2,
        "congestion": 0.0
    }
    adaptive_cfg = {
        "variance_scale": 2.0,
        "congestion_scale": 1.5,
        "floors": {"delta_threshold": 0.005, "p_win_threshold": 0.01, "min_windows": 1},
        "ceilings": {"delta_threshold": 0.05, "p_win_threshold": 0.10, "min_windows": 8}
    }

    caps = compute_adaptive_caps(base_caps, stats, adaptive_cfg)

    # variance_factor = 1.0 + 0.2 * 2.0 = 1.4
    # congestion_factor = 1.0 + 0.0 * 1.5 = 1.0
    # cap = base_cap * 1.4 * 1.0
    expected_delta = 0.02 * 1.4  # 0.028
    expected_p_win = 0.05 * 1.4  # 0.07

    assert abs(caps["delta_threshold"] - expected_delta) < 1e-9
    assert abs(caps["p_win_threshold"] - expected_p_win) < 1e-9
    assert caps["min_windows"] == int(3 * 1.4)  # 4


def test_compute_adaptive_caps_congestion_high():
    """혼잡도 높을 때 cap 증가"""
    base_caps = {
        "delta_threshold": 0.02,
        "p_win_threshold": 0.05,
        "min_windows": 3
    }
    stats = {
        "variance": 0.0,
        "congestion": 0.3
    }
    adaptive_cfg = {
        "variance_scale": 2.0,
        "congestion_scale": 1.5,
        "floors": {"delta_threshold": 0.005, "p_win_threshold": 0.01, "min_windows": 1},
        "ceilings": {"delta_threshold": 0.05, "p_win_threshold": 0.10, "min_windows": 8}
    }

    caps = compute_adaptive_caps(base_caps, stats, adaptive_cfg)

    # variance_factor = 1.0 + 0.0 * 2.0 = 1.0
    # congestion_factor = 1.0 + 0.3 * 1.5 = 1.45
    # cap = base_cap * 1.0 * 1.45
    expected_delta = 0.02 * 1.45  # 0.029
    expected_p_win = 0.05 * 1.45  # 0.0725

    assert abs(caps["delta_threshold"] - expected_delta) < 1e-9
    assert abs(caps["p_win_threshold"] - expected_p_win) < 1e-9
    assert caps["min_windows"] == int(3 * 1.45)  # 4


def test_adaptive_caps_floor_ceiling():
    """floor/ceiling 제약 준수"""
    base_caps = {
        "delta_threshold": 0.01,
        "p_win_threshold": 0.02,
        "min_windows": 1
    }
    # 극단적인 분산/혼잡도로 ceiling 초과 유도
    stats = {
        "variance": 1.0,
        "congestion": 1.0
    }
    adaptive_cfg = {
        "variance_scale": 2.0,
        "congestion_scale": 1.5,
        "floors": {"delta_threshold": 0.005, "p_win_threshold": 0.01, "min_windows": 1},
        "ceilings": {"delta_threshold": 0.05, "p_win_threshold": 0.10, "min_windows": 8}
    }

    caps = compute_adaptive_caps(base_caps, stats, adaptive_cfg)

    # Ceiling 적용
    assert caps["delta_threshold"] == 0.05
    assert caps["p_win_threshold"] == 0.10
    assert caps["min_windows"] == 8


@pytest.mark.skip(reason="Integration test - requires full environment setup")
def test_autotune_with_adaptive(tmp_path, monkeypatch):
    """autotune_promote_threshold.py 통합 테스트"""
    # Setup
    ab_history = tmp_path / "history.jsonl"
    calibration = tmp_path / "calibration.json"
    base_policy = tmp_path / "policy.json"
    guard_config = tmp_path / "guard.json"
    adaptive_config = tmp_path / "adaptive.json"
    bucket_stats = tmp_path / "bucket_stats.json"
    out_path = tmp_path / "policy.autotuned.json"

    # Mock AB history
    ab_history.write_text(json.dumps({
        "delta": 0.05,
        "p_win": 0.7,
        "n_windows": 10
    }) + "\n")

    # Mock calibration
    calibration.write_text(json.dumps({"gain": 1.0}))

    # Mock base policy
    base_policy.write_text(json.dumps({
        "promote": {"delta_threshold": 0.02, "p_win_threshold": 0.6, "min_windows": 5}
    }))

    # Mock guard config
    guard_config.write_text(json.dumps({
        "bounds": {
            "delta_threshold_min": 0.01,
            "delta_threshold_max": 0.15,
            "p_win_threshold_min": 0.55,
            "p_win_threshold_max": 0.80,
            "min_windows_min": 3,
            "min_windows_max": 15
        },
        "slew_rate": {
            "delta_threshold": 0.02,
            "p_win_threshold": 0.05,
            "min_windows": 3
        },
        "rollback": {
            "trigger": {"severity": ["critical"], "consecutive": 2},
            "last_good_path": str(tmp_path / "policy.last_good.json")
        }
    }))

    # Mock adaptive config
    adaptive_config.write_text(json.dumps({
        "caps": {
            "delta_threshold_cap": 0.02,
            "p_win_threshold_cap": 0.05,
            "min_windows_cap": 3
        },
        "variance_scale": 2.0,
        "congestion_scale": 1.5,
        "floors": {
            "delta_threshold": 0.005,
            "p_win_threshold": 0.01,
            "min_windows": 1
        },
        "ceilings": {
            "delta_threshold": 0.05,
            "p_win_threshold": 0.10,
            "min_windows": 8
        }
    }))

    # Mock bucket stats (high variance)
    bucket_stats.write_text(json.dumps({
        "variance": 0.2,
        "congestion": 0.1
    }))

    # Run autotune with adaptive
    import subprocess
    result = subprocess.run([
        "python", "jobs/autotune_promote_threshold.py",
        "--ab-history", str(ab_history),
        "--calibration", str(calibration),
        "--base-policy", str(base_policy),
        "--guard-config", str(guard_config),
        "--adaptive-config", str(adaptive_config),
        "--bucket-stats", str(bucket_stats),
        "--out", str(out_path)
    ], capture_output=True, text=True)

    # Verify
    assert result.returncode == 0
    assert out_path.exists()

    output_policy = json.loads(out_path.read_text())
    assert "promote" in output_policy
    # Adaptive caps were applied
    assert output_policy["promote"]["delta_threshold"] >= 0.01
    assert output_policy["promote"]["p_win_threshold"] >= 0.55
