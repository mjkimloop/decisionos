from pathlib import Path
from apps.rule_engine.linter import lint_rules


def test_linter_conflict_and_shadow(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    priority: 10
    stop: true
    action: {class: reject}
  - name: r2
    when: ' payload.get ( "x" , 0 ) > 0 '
    priority: 1
    action: {class: approve}
"""
    p = tmp_path / "a.yaml"
    p.write_text(content)
    issues, coverage = lint_rules(tmp_path)
    kinds = [i.kind for i in issues]
    assert "conflict" in kinds
    assert "shadow" in kinds
    assert coverage["rules"] == 2


def test_linter_duplicate_name(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    action: {class: review}
  - name: r1
    when: 'payload.get("x", 0) > 1'
    action: {class: approve}
"""
    p = tmp_path / "b.yaml"
    p.write_text(content)
    issues, _ = lint_rules(tmp_path)
    assert any(i.kind == "duplicate_name" for i in issues)

