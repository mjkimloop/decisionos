"""
Test Canary Step Adjust v1
drift severity에 따른 canary step 조정 테스트
"""
import pytest
import json
import os


def test_critical_disables_canary(tmp_path):
    """critical severity시 canary 비활성화"""
    drift_path = tmp_path / "drift.json"
    canary_config = tmp_path / "canary.json"
    out_path = tmp_path / "canary_out.json"

    # Mock drift: critical
    drift_path.write_text(json.dumps({
        "severity": "critical",
        "abs_diff": 0.3,
        "kl": 2.0
    }))

    # Mock canary config
    canary_config.write_text(json.dumps({
        "canary": {
            "enabled": True,
            "step_pct": 10,
            "max_pct": 50
        }
    }))

    # Run canary_step_adjust.py
    import subprocess
    result = subprocess.run([
        "python", "jobs/canary_step_adjust.py",
        "--drift-path", str(drift_path),
        "--canary-config", str(canary_config),
        "--out", str(out_path)
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert "[CRITICAL] Canary disabled" in result.stdout

    # Verify output
    output = json.loads(out_path.read_text())
    assert output["canary"]["enabled"] is False


def test_warn_reduces_step(tmp_path):
    """warn severity시 step/max 감속"""
    drift_path = tmp_path / "drift.json"
    canary_config = tmp_path / "canary.json"
    out_path = tmp_path / "canary_out.json"

    # Mock drift: warn
    drift_path.write_text(json.dumps({
        "severity": "warn",
        "abs_diff": 0.15,
        "kl": 1.3
    }))

    # Mock canary config
    canary_config.write_text(json.dumps({
        "canary": {
            "enabled": True,
            "step_pct": 10,
            "max_pct": 50
        }
    }))

    # Run canary_step_adjust.py
    import subprocess
    result = subprocess.run([
        "python", "jobs/canary_step_adjust.py",
        "--drift-path", str(drift_path),
        "--canary-config", str(canary_config),
        "--out", str(out_path)
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert "[WARN] Canary reduced" in result.stdout

    # Verify output
    output = json.loads(out_path.read_text())
    assert output["canary"]["enabled"] is True
    # step_pct = max(5, 10 * 0.5) = 5
    # max_pct = max(30, 50 * 0.7) = 35
    assert output["canary"]["step_pct"] == 5
    assert output["canary"]["max_pct"] == 35


def test_info_normal_step(tmp_path):
    """info severity시 정상 진행"""
    drift_path = tmp_path / "drift.json"
    canary_config = tmp_path / "canary.json"
    out_path = tmp_path / "canary_out.json"

    # Mock drift: info
    drift_path.write_text(json.dumps({
        "severity": "info",
        "abs_diff": 0.05,
        "kl": 0.5
    }))

    # Mock canary config (initially reduced)
    canary_config.write_text(json.dumps({
        "canary": {
            "enabled": True,
            "step_pct": 5,
            "max_pct": 30
        }
    }))

    # Run canary_step_adjust.py
    import subprocess
    result = subprocess.run([
        "python", "jobs/canary_step_adjust.py",
        "--drift-path", str(drift_path),
        "--canary-config", str(canary_config),
        "--out", str(out_path)
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert "[INFO] Canary normal" in result.stdout

    # Verify output
    output = json.loads(out_path.read_text())
    assert output["canary"]["enabled"] is True
    assert output["canary"]["step_pct"] == 10
    assert output["canary"]["max_pct"] == 50
