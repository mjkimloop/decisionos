from types import SimpleNamespace

from scripts.ci.annotate_release_gate import build_comment, MARKER


def test_comment_contains_marker():
    args = SimpleNamespace()
    comment = build_comment(
        args,
        {"pre_gate": "pass", "gate": "warn", "post_gate": "fail"},
        "artifacts",
        "reasons",
        "",
        "diff-link",
        [],
        "",
        "",
        {},
        {},
        "",
        "",
    )
    assert MARKER in comment
    assert "artifacts" in comment.lower()
