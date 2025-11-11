import json
import pytest
from pathlib import Path

pytestmark = [pytest.mark.gate_q]

@pytest.fixture(autouse=True)
def stage_key(monkeypatch):
    monkeypatch.setenv("DECISIONOS_STAGE_KEY", "test-key")
    monkeypatch.setenv("DECISIONOS_STAGE_KEY_ID", "test")

def test_auto_promote_with_N_passes(tmp_path, monkeypatch):
    """N consecutive passes without burst → promote"""
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "meta": {"tenant": "test"},
        "canary": {
            "windows": [
                {"pass": True, "burst": 0},
                {"pass": True, "burst": 0},
                {"pass": True, "burst": 0},
            ]
        }
    }), encoding="utf-8")

    stage_dir = tmp_path / "rollout"
    stage_dir.mkdir(parents=True, exist_ok=True)
    stage_file = stage_dir / "stage.txt"
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(evidence))
    monkeypatch.setenv("STAGE_PATH", str(stage_file))
    
    from jobs.canary_auto_promote import main
    try:
        main()
        assert False, "Should exit 0"
    except SystemExit as e:
        assert e.code == 0
    
    assert stage_file.read_text(encoding="utf-8").strip() == "promote"

def test_auto_abort_with_burst(tmp_path, monkeypatch):
    """Burst detected → abort"""
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "meta": {"tenant": "test"},
        "canary": {
            "windows": [
                {"pass": True, "burst": 0},
                {"pass": True, "burst": 5},  # burst!
                {"pass": True, "burst": 0},
            ]
        }
    }), encoding="utf-8")

    stage_dir = tmp_path / "rollout"
    stage_dir.mkdir(parents=True, exist_ok=True)
    stage_file = stage_dir / "stage.txt"
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(evidence))
    monkeypatch.setenv("STAGE_PATH", str(stage_file))
    
    from jobs.canary_auto_promote import main
    try:
        main()
        assert False, "Should exit 2"
    except SystemExit as e:
        assert e.code == 2
    
    assert stage_file.read_text(encoding="utf-8").strip() == "abort"
