import pytest
import os
import json
import subprocess
import sys

pytestmark = [pytest.mark.gate_ops]


def test_robust_scale():
    """MAD 기반 robust scale 계산"""
    from apps.ops.optimizer.autotune import robust_scale
    values = [1.0, 2.0, 3.0, 100.0]  # 극단값 포함
    scale = robust_scale(values)
    assert scale > 0
    # MAD는 중앙값 편차의 중앙값 * 1.4826
    # median=2.5, deviations=[1.5, 0.5, 0.5, 97.5], MAD=1.0, scale≈1.48
    assert 1.0 <= scale <= 3.0


def test_suggest_thresholds_basic():
    """기본 임계 제안"""
    from apps.ops.optimizer.autotune import suggest_thresholds
    ab_reports = [
        {"delta": {"mean": 1.0}, "p_win": 0.6},
        {"delta": {"mean": 1.5}, "p_win": 0.7},
        {"delta": {"mean": 0.8}, "p_win": 0.65}
    ]
    res = suggest_thresholds(ab_reports, calibration_gain=1.0, safety_factor=2.0)
    assert "delta_threshold" in res
    assert "p_win_threshold" in res
    assert "min_windows" in res
    assert res["method"] == "robust_mad"
    assert res["min_windows"] >= 3


def test_suggest_thresholds_empty():
    """빈 리포트 처리"""
    from apps.ops.optimizer.autotune import suggest_thresholds
    res = suggest_thresholds([], calibration_gain=1.0)
    assert res["delta_threshold"] == 0.0
    assert res["p_win_threshold"] == 0.5
    assert res["method"] == "empty"


def test_autotune_job(tmp_path):
    """Autotune 작업 실행"""
    # AB 히스토리 준비
    history = [
        {"delta": {"mean": 1.0}, "p_win": 0.6},
        {"delta": {"mean": 1.5}, "p_win": 0.7}
    ]
    hist_path = tmp_path / "history.jsonl"
    with open(hist_path, "w", encoding="utf-8") as f:
        for h in history:
            f.write(json.dumps(h) + "\n")

    # Calibration
    cal_path = tmp_path / "calibration.json"
    cal_path.write_text(json.dumps({"gain": 0.9}), encoding="utf-8")

    out_path = tmp_path / "policy.json"

    subprocess.check_call([
        sys.executable, "-m", "jobs.autotune_promote_threshold",
        "--ab-history", str(hist_path),
        "--calibration", str(cal_path),
        "--out", str(out_path),
        "--safety-factor", "2.0"
    ])

    policy = json.loads(out_path.read_text(encoding="utf-8"))
    assert "delta_threshold" in policy
    assert "p_win_threshold" in policy
    assert policy["min_windows"] >= 2
