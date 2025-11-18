from scripts.change import break_glass


def test_break_glass_issue_and_verify(policy_keys, monkeypatch, tmp_path):
    manifest = tmp_path / "break.json"
    monkeypatch.setenv("DECISIONOS_BREAK_GLASS_MANIFEST", str(manifest))
    payload = break_glass.issue_token("incident", "alice", ttl=30, token="test-token")
    assert manifest.exists()
    assert payload["manifest"]["token"] == "test-token"
    assert break_glass.verify_token("test-token")
    assert not break_glass.verify_token("wrong")
