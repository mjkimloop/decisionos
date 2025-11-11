import json
import pytest

def test_policy_v2_defaults_and_schedule(tmp_path):
    """Policy v2 defaults 및 step_schedule 검증"""
    p = {
        "consecutive_passes": 2,
        "step_schedule": [{"pct": 10, "min_duration_sec": 60}]
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(p), encoding="utf-8")

    from jobs.canary_auto_promote import _load_policy
    out = _load_policy(str(f))

    assert out["cooldown_sec"] >= 0
    assert out["step_schedule"][0]["pct"] == 10
    assert out["consecutive_passes"] == 2


def test_policy_v2_all_fields(tmp_path):
    """모든 v2 필드 검증"""
    p = {
        "consecutive_passes": 3,
        "grace_burst": 0,
        "max_step_pct": 25,
        "holdback_pct_min": 5,
        "cooldown_sec": 300,
        "stickiness": "ip",
        "ewma_tolerance": 0.35,
        "burst_threshold": 0.6,
        "step_schedule": [
            {"pct": 5, "min_duration_sec": 300},
            {"pct": 10, "min_duration_sec": 300}
        ]
    }
    f = tmp_path / "full_policy.json"
    f.write_text(json.dumps(p), encoding="utf-8")

    from jobs.canary_auto_promote import _load_policy
    out = _load_policy(str(f))

    assert out["consecutive_passes"] == 3
    assert out["holdback_pct_min"] == 5
    assert out["cooldown_sec"] == 300
    assert out["stickiness"] == "ip"
    assert out["ewma_tolerance"] == 0.35
    assert out["burst_threshold"] == 0.6
    assert len(out["step_schedule"]) == 2


def test_policy_v2_defaults_applied(tmp_path):
    """빠진 필드에 defaults 적용 확인"""
    p = {"consecutive_passes": 5}
    f = tmp_path / "minimal.json"
    f.write_text(json.dumps(p), encoding="utf-8")

    from jobs.canary_auto_promote import _load_policy
    out = _load_policy(str(f))

    # defaults 적용 확인
    assert out["holdback_pct_min"] == 0
    assert out["cooldown_sec"] == 300
    assert out["stickiness"] == "none"
    assert out["ewma_tolerance"] == 0.3
    assert out["burst_threshold"] == 0.5
    assert out["step_schedule"] == []


def test_policy_v2_step_schedule_structure(tmp_path):
    """step_schedule 구조 검증"""
    p = {
        "step_schedule": [
            {"pct": 5, "min_duration_sec": 300},
            {"pct": 25, "min_duration_sec": 600},
            {"pct": 50, "min_duration_sec": 900}
        ]
    }
    f = tmp_path / "schedule.json"
    f.write_text(json.dumps(p), encoding="utf-8")

    from jobs.canary_auto_promote import _load_policy
    out = _load_policy(str(f))

    schedule = out["step_schedule"]
    assert len(schedule) == 3
    assert schedule[0]["pct"] == 5
    assert schedule[1]["min_duration_sec"] == 600
    assert schedule[2]["pct"] == 50
