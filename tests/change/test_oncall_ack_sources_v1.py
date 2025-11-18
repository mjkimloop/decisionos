from scripts.change import require_oncall_ack


def test_oncall_ack(policy_keys, tmp_path):
    status = tmp_path / "status.json"
    rc_fail = require_oncall_ack.main(
        [
            "--service",
            "ops-api",
            "--ack-users",
            "nobody",
            "--status-file",
            str(status),
        ]
    )
    assert rc_fail == 2

    rc_ok = require_oncall_ack.main(
        [
            "--service",
            "ops-api",
            "--ack-users",
            "ops-primary",
            "--status-file",
            str(status),
        ]
    )
    assert rc_ok == 0
