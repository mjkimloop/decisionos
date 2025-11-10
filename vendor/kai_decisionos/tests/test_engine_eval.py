from pathlib import Path
import pytest

from apps.rule_engine.engine import RuleSet, evaluate_rules, safe_eval


def test_priority_and_stop(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: high
    when: 'payload.get("x", 0) > 0'
    priority: 10
    stop: true
    action:
      class: reject
      reasons: ["high"]
  - name: low
    when: 'payload.get("x", 0) > 0'
    priority: 1
    action:
      class: approve
      reasons: ["low"]
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)
    out = evaluate_rules(rs, {"x": 1})
    assert out["class"] == "reject"
    assert out["rules_applied"] == ["high"]


def test_safe_eval_blocks_call():
    with pytest.raises(ValueError):
        safe_eval("__import__('os')", {"payload": {}})


def test_ruleset_load_priority_stop(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: a
    when: 'payload.get("y", 0) == 1'
    priority: 5
    stop: false
    action: {class: review}
"""
    f = tmp_path / "r.yaml"
    f.write_text(content)
    rs = RuleSet.load(f)
    assert rs.rules[0].priority == 5
    assert rs.rules[0].stop is False


def test_merge_reasons_docs_no_dupes(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("z", 0) > 1'
    action:
      class: review
      reasons: ["a","a"]
      required_docs: ["d1","d1"]
"""
    f = tmp_path / "r.yaml"
    f.write_text(content)
    rs = RuleSet.load(f)
    out = evaluate_rules(rs, {"z": 2})
    assert out["class"] == "review"
    assert out["reasons"] == ["a"]
    assert out["required_docs"] == ["d1"]


def test_error_captured_in_rules_applied(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: bad
    when: 'open(\"/etc/passwd\")'
    action: {class: review}
"""
    f = tmp_path / "r.yaml"
    f.write_text(content)
    rs = RuleSet.load(f)
    out = evaluate_rules(rs, {"k": 1})
    assert any("ERROR:" in x for x in out["rules_applied"]) or out["rules_applied"] == []

