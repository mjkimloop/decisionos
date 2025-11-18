import json
from pathlib import Path

from scripts.change import require_cab_multisig, require_oncall_ack, verify_freeze_window


def test_ci_change_governance_flow(policy_keys, tmp_path):
    status = tmp_path / "change.json"
    reasons = tmp_path / "reasons.json"
    assert (
        verify_freeze_window.main(
            [
                "--service",
                "ops-api",
                "--labels",
                "hotfix",
                "--status-file",
                str(status),
                "--reasons-json",
                str(reasons),
            ]
        )
        == 0
    )
    assert (
        require_cab_multisig.main(
            [
                "--service",
                "ops-api",
                "--signers",
                "alice,bob",
                "--status-file",
                str(status),
            ]
        )
        == 0
    )
    assert (
        require_oncall_ack.main(
            [
                "--service",
                "ops-api",
                "--ack-users",
                "ops-primary",
                "--status-file",
                str(status),
            ]
        )
        == 0
    )
    data = json.loads(status.read_text(encoding="utf-8"))
    assert any(entry["name"] == "freeze" for entry in data)
    assert any(entry["name"] == "cab" for entry in data)
    assert any(entry["name"] == "oncall" for entry in data)
