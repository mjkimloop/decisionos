"""
Test Risk to Stage End-to-End v1
통합 테스트: 신호 → risk → stage
"""
import pytest
import json
import subprocess
from pathlib import Path


@pytest.mark.skip(reason="Integration test - requires full environment")
def test_end_to_end_flow(tmp_path):
    """신호 입력 → risk 계산 → stage 파일 생성 검증"""
    signals_path = tmp_path / "signals.json"
    stage_out = tmp_path / "desired_stage.txt"
    meta_out = tmp_path / "desired_meta.json"

    # Mock signals (low risk)
    signals_path.write_text(json.dumps({
        "drift_z": 0.0,
        "anomaly_score": 0.0,
        "infra_p95_ms": 300,
        "error_rate": 0.0,
        "quota_denies": 0,
        "budget_level": "ok"
    }))

    result = subprocess.run([
        "python", "-m", "jobs.risk_decide_and_stage",
        "--signals", str(signals_path),
        "--stage-out", str(stage_out),
        "--meta-out", str(meta_out)
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert stage_out.exists()
    assert meta_out.exists()

    # Stage should be "promote" for low risk
    stage = stage_out.read_text().strip()
    assert stage == "promote"

    # Meta should have risk_score and action
    meta = json.loads(meta_out.read_text())
    assert "risk_score" in meta
    assert meta["risk_score"] < 0.3
    assert meta["action"]["mode"] == "promote"
