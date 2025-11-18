import tempfile

from scripts.change import verify_freeze_window


def test_freeze_window_blocks_without_tag(policy_keys, tmp_path):
    status = tmp_path / "status.json"
    reasons = tmp_path / "reasons.json"
    rc = verify_freeze_window.main(
        [
            "--service",
            "ops-api",
            "--now",
            "2025-11-22T00:00:00Z",
            "--status-file",
            str(status),
            "--reasons-json",
            str(reasons),
        ]
    )
    assert rc == 2
    assert status.exists()
    assert reasons.exists()


def test_freeze_window_allows_hotfix(policy_keys, tmp_path):
    status = tmp_path / "status.json"
    rc = verify_freeze_window.main(
        [
            "--service",
            "ops-api",
            "--labels",
            "hotfix",
            "--now",
            "2025-11-22T00:00:00Z",
            "--status-file",
            str(status),
        ]
    )
    assert rc == 0
