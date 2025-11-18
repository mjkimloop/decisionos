from scripts.change import require_cab_multisig


def test_cab_multisig_requires_signers(policy_keys, tmp_path):
    status = tmp_path / "status.json"
    rc = require_cab_multisig.main(
        [
            "--service",
            "ops-api",
            "--signers",
            "alice,bob",
            "--status-file",
            str(status),
        ]
    )
    assert rc == 0
    rc_block = require_cab_multisig.main(
        [
            "--service",
            "ops-api",
            "--signers",
            "alice",
            "--status-file",
            str(status),
        ]
    )
    assert rc_block == 2
