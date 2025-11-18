"""
카나리 자동 승격 정책 튜닝 테스트 (v0.5.11r-4)

튜닝 파라미터:
- required_pass_windows: 3 → 5
- max_burst: 0 → 1
- min_observation_minutes: 0 → 30
"""
import json
import importlib
import pytest
import time

pytestmark = [pytest.mark.gate_ah]

@pytest.fixture(autouse=True)
def stage_key(monkeypatch):
    monkeypatch.setenv("DECISIONOS_STAGE_KEY", "test-key")
    monkeypatch.setenv("DECISIONOS_STAGE_KEY_ID", "test")

def test_canary_tuning_5_consecutive_passes(tmp_path, monkeypatch):
    """5연속 통과 + burst ≤1 → promote"""
    now = time.time()
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0, "timestamp_unix": now},
                {"pass": True, "burst": 1, "timestamp_unix": now + 600},  # 10분 후
                {"pass": True, "burst": 0, "timestamp_unix": now + 1200},
                {"pass": True, "burst": 0, "timestamp_unix": now + 1800},
                {"pass": True, "burst": 0, "timestamp_unix": now + 2400},  # 40분 후 (30분 초과)
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "5")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1")
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30")

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 0  # promote

def test_canary_tuning_burst_tolerance(tmp_path, monkeypatch):
    """버스트 1회는 허용, 2회 이상은 abort"""
    now = time.time()
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0, "timestamp_unix": now},
                {"pass": True, "burst": 1, "timestamp_unix": now + 600},
                {"pass": True, "burst": 2, "timestamp_unix": now + 1200},  # burst > 1
                {"pass": True, "burst": 0, "timestamp_unix": now + 1800},
                {"pass": True, "burst": 0, "timestamp_unix": now + 2400},
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "5")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1")
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30")
    burst_log = tmp_path / "burst.json"
    monkeypatch.setenv("DECISIONOS_CANARY_BURST_LOG", str(burst_log))

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 2  # abort
    logged = json.loads(burst_log.read_text(encoding="utf-8"))
    assert logged.get("cause") == "burst_threshold"
    assert logged.get("max_burst") == 1.0
    assert logged.get("recent_window_count") == 5
    assert isinstance(logged.get("windows"), list) and logged["windows"]

def test_canary_tuning_min_observation_time(tmp_path, monkeypatch):
    """30분 미만 관찰 시 hold"""
    now = time.time()
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0, "timestamp_unix": now},
                {"pass": True, "burst": 0, "timestamp_unix": now + 300},  # 5분
                {"pass": True, "burst": 0, "timestamp_unix": now + 600},  # 10분
                {"pass": True, "burst": 0, "timestamp_unix": now + 900},  # 15분
                {"pass": True, "burst": 0, "timestamp_unix": now + 1200},  # 20분 (< 30분)
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "5")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1")
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30")

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 3  # hold

def test_canary_tuning_4_passes_hold(tmp_path, monkeypatch):
    """4연속 통과는 부족 → hold"""
    now = time.time()
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0, "timestamp_unix": now},
                {"pass": True, "burst": 0, "timestamp_unix": now + 600},
                {"pass": True, "burst": 0, "timestamp_unix": now + 1200},
                {"pass": True, "burst": 0, "timestamp_unix": now + 1800},
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "5")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1")
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30")

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 3  # hold

def test_canary_tuning_one_fail_in_5_hold(tmp_path, monkeypatch):
    """5개 중 1개 실패 → hold"""
    now = time.time()
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0, "timestamp_unix": now},
                {"pass": True, "burst": 0, "timestamp_unix": now + 600},
                {"pass": False, "burst": 0, "timestamp_unix": now + 1200},  # 실패
                {"pass": True, "burst": 0, "timestamp_unix": now + 1800},
                {"pass": True, "burst": 0, "timestamp_unix": now + 2400},
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "5")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1")
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30")

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 3  # hold

def test_canary_tuning_exactly_30min_promote(tmp_path, monkeypatch):
    """정확히 30분 관찰 시 promote"""
    now = time.time()
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0, "timestamp_unix": now},
                {"pass": True, "burst": 0, "timestamp_unix": now + 450},
                {"pass": True, "burst": 0, "timestamp_unix": now + 900},
                {"pass": True, "burst": 0, "timestamp_unix": now + 1350},
                {"pass": True, "burst": 0, "timestamp_unix": now + 1800},  # 정확히 30분
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "5")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1")
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30")

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 0  # promote
