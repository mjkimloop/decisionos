"""
Test Burn Rate Gate v1
버짓 소모율 게이트 테스트
"""
import pytest
import json
import subprocess
from pathlib import Path


@pytest.mark.gate_u
def test_burn_rate_normal(tmp_path):
    """소모율 0.5x → 통과"""
    metrics_path = tmp_path / "errors.json"
    config_path = tmp_path / "burn_rate.json"
    evidence_path = tmp_path / "gate_reasons.jsonl"

    # Mock metrics: 5 errors / 1000 total
    # Target: 0.995 → error budget 0.005 → expected_error_rate = 0.005
    # Actual: 5/1000 = 0.005
    # Burn rate = 0.005 / 0.005 = 1.0 (정상 소모)
    # 하지만 1.0은 warn 임계이므로, 0.5x가 되려면 더 적은 에러 필요
    metrics_path.write_text(json.dumps({"errors": 2, "total": 1000}))

    config_path.write_text(json.dumps({
        "objective": {"target_availability": 0.995},
        "window_sec": 3600,
        "thresholds": {"warn": 1.0, "critical": 2.0}
    }))

    result = subprocess.run([
        "python", "-m", "jobs.burnrate_gate",
        "--metrics", str(metrics_path),
        "--config", str(config_path),
        "--evidence", str(evidence_path)
    ], capture_output=True, text=True)

    # Should pass (exit 0)
    assert result.returncode == 0
    assert "[OK]" in result.stdout


@pytest.mark.gate_u
def test_burn_rate_warn(tmp_path):
    """소모율 1.2x → warn 로그만"""
    metrics_path = tmp_path / "errors.json"
    config_path = tmp_path / "burn_rate.json"
    evidence_path = tmp_path / "gate_reasons.jsonl"

    # Burn rate = 1.2x
    # Target: 0.995 → error budget 0.005
    # Expected errors: 1000 * 0.005 = 5
    # Actual errors: 6 → burn_rate = 6/5 = 1.2
    metrics_path.write_text(json.dumps({"errors": 6, "total": 1000}))

    config_path.write_text(json.dumps({
        "objective": {"target_availability": 0.995},
        "window_sec": 3600,
        "thresholds": {"warn": 1.0, "critical": 2.0}
    }))

    result = subprocess.run([
        "python", "-m", "jobs.burnrate_gate",
        "--metrics", str(metrics_path),
        "--config", str(config_path),
        "--evidence", str(evidence_path)
    ], capture_output=True, text=True)

    # Should pass (exit 0) but with warn log
    assert result.returncode == 0
    assert "[WARN]" in result.stdout


@pytest.mark.gate_u
def test_burn_rate_critical(tmp_path):
    """소모율 2.1x → exit(2) + reason:budget-burn"""
    metrics_path = tmp_path / "errors.json"
    config_path = tmp_path / "burn_rate.json"
    evidence_path = tmp_path / "gate_reasons.jsonl"

    # Burn rate = 2.1x
    # Expected errors: 1000 * 0.005 = 5
    # Actual errors: 11 → burn_rate = 11/5 = 2.2
    metrics_path.write_text(json.dumps({"errors": 11, "total": 1000}))

    config_path.write_text(json.dumps({
        "objective": {"target_availability": 0.995},
        "window_sec": 3600,
        "thresholds": {"warn": 1.0, "critical": 2.0}
    }))

    result = subprocess.run([
        "python", "-m", "jobs.burnrate_gate",
        "--metrics", str(metrics_path),
        "--config", str(config_path),
        "--evidence", str(evidence_path)
    ], capture_output=True, text=True)

    # Should fail (exit 2)
    assert result.returncode == 2
    assert "[CRITICAL]" in result.stdout

    # Evidence should contain reason:budget-burn
    assert evidence_path.exists()
    evidence = evidence_path.read_text()
    assert "reason:budget-burn" in evidence
