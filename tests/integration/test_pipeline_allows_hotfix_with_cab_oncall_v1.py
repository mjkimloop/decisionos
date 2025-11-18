import os
import subprocess
import sys


def run(cmd, env):
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_pipeline_allows_hotfix(tmp_path):
    env = os.environ.copy()
    env["DECISIONOS_POLICY_KEYS"] = '[{"key_id":"policy-local","secret":"policy-local-secret","state":"active"}]'
    status = tmp_path / "status.json"
    run(
        [
            sys.executable,
            "-m",
            "scripts.change.verify_freeze_window",
            "--service",
            "ops-api",
            "--labels",
            "hotfix",
            "--status-file",
            str(status),
        ],
        env,
    )
    run(
        [
            sys.executable,
            "-m",
            "scripts.change.require_cab_multisig",
            "--service",
            "ops-api",
            "--signers",
            "alice,bob",
            "--status-file",
            str(status),
        ],
        env,
    )
    run(
        [
            sys.executable,
            "-m",
            "scripts.change.require_oncall_ack",
            "--service",
            "ops-api",
            "--ack-users",
            "ops-primary",
            "--status-file",
            str(status),
        ],
        env,
    )
