from pathlib import Path
from apps.rule_engine.linter import lint_rules


def test_linter_detects_conflict_and_shadow(tmp_path: Path):
    a = tmp_path / "a.yaml"
    a.write_text(
        """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("x",0) > 1'
    priority: 10
    stop: true
    action: {class: reject}
  - name: r2
    when: ' payload.get ( "x" , 0 ) > 1 '
    priority: 1
    action: {class: approve}
        """,
        encoding="utf-8",
    )
    issues, cov = lint_rules(tmp_path)
    kinds = [i.kind for i in issues]
    assert "conflict" in kinds and "shadow" in kinds

