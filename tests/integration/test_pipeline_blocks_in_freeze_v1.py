import os
import subprocess
import sys


def test_pipeline_blocks_in_freeze(tmp_path):
    env = os.environ.copy()
    env["DECISIONOS_POLICY_KEYS"] = '[{"key_id":"policy-local","secret":"policy-local-secret","state":"active"}]'
    cmd = [
        sys.executable,
        "-m",
        "scripts.change.verify_freeze_window",
        "--service",
        "ops-api",
        "--now",
        "2025-11-21T00:00:00Z",
        "--status-file",
        str(tmp_path / "status.json"),
        "--reasons-json",
        str(tmp_path / "reasons.json"),
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "freeze" in result.stdout
