import sys


def run_module(module, argv):
    old = sys.argv
    sys.argv = argv
    try:
        return __import__(module, fromlist=["main"]).main()
    finally:
        sys.argv = old


def test_label_sync_skips_without_token(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("DECISIONOS_VISIBILITY_ENABLE", "1")
    monkeypatch.setenv("PRE_GATE_RESULT", "success")
    monkeypatch.setenv("GATE_RESULT", "success")
    monkeypatch.setenv("POST_GATE_RESULT", "success")
    out = tmp_path / "body.md"
    rc = run_module(
        "scripts.ci.annotate_release_gate",
        [
            "annotate_release_gate.py",
            "--output",
            str(out),
            "--sync-labels",
        ],
    )
    assert rc == 0
