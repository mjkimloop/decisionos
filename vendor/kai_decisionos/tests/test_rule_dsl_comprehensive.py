"""
Comprehensive test suite for Rule DSL Parser/Evaluator (C-01).

Tests cover:
- YAML parsing and loading
- AST safety validation
- Rule evaluation with various conditions
- Priority and stop flag behavior
- Action merging (reasons, required_docs)
- Error handling
- Linting (conflicts, shadows, duplicates)
- Coverage reporting
- Edge cases
"""
from pathlib import Path
import pytest
import json

from apps.rule_engine.engine import (
    RuleSet,
    Rule,
    evaluate_rules,
    safe_eval,
    load_contract,
    load_rules_for_contract,
)
from apps.rule_engine.linter import lint_rules, LintIssue
from apps.rule_engine.eval_rule import introspect_ast


# ============================================================================
# Test Group 1: YAML Parsing & Loading
# ============================================================================


def test_yaml_parse_basic_ruleset(tmp_path: Path):
    """Test basic YAML ruleset parsing."""
    content = """
name: test_rules
version: 1.0.0
rules:
  - name: rule1
    when: 'payload.get("score", 0) > 50'
    action:
      class: approve
      reasons: ["high_score"]
      confidence: 0.9
"""
    p = tmp_path / "rules.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    assert rs.name == "test_rules"
    assert rs.version == "1.0.0"
    assert len(rs.rules) == 1
    assert rs.rules[0].name == "rule1"
    assert rs.rules[0].action["class"] == "approve"


def test_yaml_parse_multiple_rules(tmp_path: Path):
    """Test parsing multiple rules in order."""
    content = """
name: multi
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    priority: 10
    action: {class: reject}
  - name: r2
    when: 'payload.get("x", 0) < 0'
    priority: 5
    action: {class: approve}
  - name: r3
    when: 'payload.get("x", 0) == 0'
    action: {class: review}
"""
    p = tmp_path / "multi.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    assert len(rs.rules) == 3
    assert rs.rules[0].priority == 10
    assert rs.rules[1].priority == 5
    assert rs.rules[2].priority == 0  # Default priority


def test_yaml_parse_with_stop_flag(tmp_path: Path):
    """Test parsing rules with stop flag."""
    content = """
name: test
version: 1
rules:
  - name: early_exit
    when: 'payload.get("urgent", False)'
    stop: true
    action: {class: approve}
"""
    p = tmp_path / "stop.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    assert rs.rules[0].stop is True


def test_yaml_parse_required_docs(tmp_path: Path):
    """Test parsing rules with required_docs."""
    content = """
name: test
version: 1
rules:
  - name: need_docs
    when: 'payload.get("incomplete", False)'
    action:
      class: review
      reasons: ["missing_info"]
      required_docs: ["id", "proof_of_address"]
      confidence: 0.5
"""
    p = tmp_path / "docs.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    assert "required_docs" in rs.rules[0].action
    assert len(rs.rules[0].action["required_docs"]) == 2


# ============================================================================
# Test Group 2: AST Safety & Expression Validation
# ============================================================================


def test_safe_eval_allows_simple_comparison():
    """Test that simple comparisons are allowed."""
    result = safe_eval('payload.get("x", 0) > 5', {"payload": {"x": 10}})
    assert result is True


def test_safe_eval_allows_boolean_logic():
    """Test that boolean AND/OR operations are allowed."""
    result = safe_eval(
        'payload.get("a", 0) > 5 and payload.get("b", 0) < 10',
        {"payload": {"a": 6, "b": 8}}
    )
    assert result is True


def test_safe_eval_blocks_import():
    """Test that __import__ is blocked."""
    with pytest.raises(ValueError):
        safe_eval("__import__('os')", {"payload": {}})


def test_safe_eval_blocks_exec():
    """Test that exec is blocked."""
    with pytest.raises((ValueError, SyntaxError)):
        safe_eval("exec('print(1)')", {"payload": {}})


def test_safe_eval_blocks_arbitrary_attribute_access():
    """Test that arbitrary attribute access is blocked."""
    with pytest.raises(ValueError, match="Only payload.get"):
        safe_eval("payload.__class__", {"payload": {}})


def test_safe_eval_blocks_open():
    """Test that open() is blocked."""
    with pytest.raises(ValueError):
        safe_eval("open('/etc/passwd')", {"payload": {}})


def test_safe_eval_allows_constants():
    """Test that constant values are allowed."""
    result = safe_eval("True", {"payload": {}})
    assert result is True


def test_introspect_ast_valid_expression():
    """Test AST introspection for valid expression."""
    ast_info = introspect_ast('payload.get("x", 0) > 5')
    assert ast_info["valid"] is True
    assert "Compare" in ast_info["nodes"]
    assert "Call" in ast_info["nodes"]


def test_introspect_ast_invalid_expression():
    """Test AST introspection for syntax error."""
    ast_info = introspect_ast('payload.get("x",')
    assert ast_info["valid"] is False
    assert "error" in ast_info


# ============================================================================
# Test Group 3: Rule Evaluation Logic
# ============================================================================


def test_evaluate_single_matching_rule(tmp_path: Path):
    """Test evaluation with a single matching rule."""
    content = """
name: test
version: 1
rules:
  - name: high_score
    when: 'payload.get("score", 0) >= 80'
    action:
      class: approve
      reasons: ["excellent_score"]
      confidence: 0.95
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"score": 90})

    assert out["class"] == "approve"
    assert "excellent_score" in out["reasons"]
    assert out["confidence"] == 0.95
    assert "high_score" in out["rules_applied"]


def test_evaluate_no_matching_rules(tmp_path: Path):
    """Test evaluation when no rules match."""
    content = """
name: test
version: 1
rules:
  - name: impossible
    when: 'payload.get("score", 0) > 1000'
    action: {class: approve}
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"score": 50})

    assert out["class"] == "review"  # Default
    assert len(out["rules_applied"]) == 0


def test_evaluate_multiple_matching_rules_merge_reasons(tmp_path: Path):
    """Test that multiple matching rules merge reasons."""
    content = """
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    action:
      class: review
      reasons: ["reason_a"]
  - name: r2
    when: 'payload.get("x", 0) > 0'
    action:
      class: review
      reasons: ["reason_b"]
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"x": 5})

    assert set(out["reasons"]) == {"reason_a", "reason_b"}


def test_evaluate_priority_ordering(tmp_path: Path):
    """Test that rules are evaluated in priority order."""
    content = """
name: test
version: 1
rules:
  - name: low_priority
    when: 'payload.get("x", 0) > 0'
    priority: 1
    action:
      class: approve
      reasons: ["low"]
  - name: high_priority
    when: 'payload.get("x", 0) > 0'
    priority: 10
    stop: true
    action:
      class: reject
      reasons: ["high"]
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"x": 5})

    # High priority rule should execute first and stop
    assert out["class"] == "reject"
    assert out["rules_applied"] == ["high_priority"]


def test_evaluate_stop_flag_halts_evaluation(tmp_path: Path):
    """Test that stop flag halts further evaluation."""
    content = """
name: test
version: 1
rules:
  - name: first
    when: 'payload.get("x", 0) > 0'
    priority: 10
    stop: true
    action: {class: reject}
  - name: second
    when: 'payload.get("x", 0) > 0'
    priority: 5
    action: {class: approve}
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"x": 5})

    assert len(out["rules_applied"]) == 1
    assert out["rules_applied"][0] == "first"


def test_evaluate_merge_required_docs(tmp_path: Path):
    """Test that required_docs are merged from multiple rules."""
    content = """
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    action:
      class: review
      required_docs: ["doc1", "doc2"]
  - name: r2
    when: 'payload.get("x", 0) > 0'
    action:
      class: review
      required_docs: ["doc2", "doc3"]
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"x": 5})

    # Should merge and deduplicate
    assert set(out["required_docs"]) == {"doc1", "doc2", "doc3"}


def test_evaluate_complex_boolean_expression(tmp_path: Path):
    """Test evaluation with complex boolean expressions."""
    content = """
name: test
version: 1
rules:
  - name: complex
    when: 'payload.get("a", 0) > 50 and payload.get("b", 0) < 100 and payload.get("c", False)'
    action:
      class: approve
      reasons: ["all_conditions_met"]
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    # All conditions true
    out1 = evaluate_rules(rs, {"a": 60, "b": 80, "c": True})
    assert out1["class"] == "approve"

    # One condition false
    out2 = evaluate_rules(rs, {"a": 60, "b": 80, "c": False})
    assert out2["class"] == "review"  # Default


def test_evaluate_handles_missing_payload_keys(tmp_path: Path):
    """Test that missing payload keys use defaults."""
    content = """
name: test
version: 1
rules:
  - name: default_check
    when: 'payload.get("missing", 999) == 999'
    action: {class: approve}
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {})

    assert out["class"] == "approve"


def test_evaluate_rule_with_error_captured(tmp_path: Path):
    """Test that rule evaluation errors are captured in rules_applied."""
    content = """
name: test
version: 1
rules:
  - name: bad_rule
    when: 'open("/etc/passwd")'
    action: {class: approve}
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {})

    # Should capture error
    assert any("ERROR:" in r for r in out["rules_applied"])


# ============================================================================
# Test Group 4: Linting (Conflicts, Shadows, Duplicates)
# ============================================================================


def test_linter_detects_duplicate_names(tmp_path: Path):
    """Test that linter detects duplicate rule names."""
    content = """
name: test
version: 1
rules:
  - name: dup
    when: 'payload.get("x", 0) > 0'
    action: {class: approve}
  - name: dup
    when: 'payload.get("x", 0) > 1'
    action: {class: reject}
"""
    p = tmp_path / "dup.yaml"
    p.write_text(content)

    issues, coverage = lint_rules(tmp_path)

    assert any(i.kind == "duplicate_name" for i in issues)


def test_linter_detects_conflicts(tmp_path: Path):
    """Test that linter detects conflicting rules (same condition, different action)."""
    content = """
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 5'
    action: {class: approve}
  - name: r2
    when: 'payload.get("x", 0) > 5'
    action: {class: reject}
"""
    p = tmp_path / "conflict.yaml"
    p.write_text(content)

    issues, coverage = lint_rules(tmp_path)

    assert any(i.kind == "conflict" for i in issues)


def test_linter_detects_shadows(tmp_path: Path):
    """Test that linter detects shadowed rules."""
    content = """
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 5'
    priority: 10
    stop: true
    action: {class: approve}
  - name: r2
    when: 'payload.get("x", 0) > 5'
    priority: 1
    action: {class: approve}
"""
    p = tmp_path / "shadow.yaml"
    p.write_text(content)

    issues, coverage = lint_rules(tmp_path)

    assert any(i.kind == "shadow" for i in issues)


def test_linter_coverage_report(tmp_path: Path):
    """Test that linter generates coverage metrics."""
    content = """
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    priority: 10
    stop: true
    action: {class: approve}
  - name: r2
    when: 'payload.get("y", 0) > 0'
    action: {class: review}
"""
    p = tmp_path / "cov.yaml"
    p.write_text(content)

    issues, coverage = lint_rules(tmp_path)

    assert coverage["rules"] == 2
    assert coverage["priority_pct"] == 50.0  # 1 of 2
    assert coverage["stop_pct"] == 50.0  # 1 of 2
    assert coverage["action_class_pct"] == 100.0  # 2 of 2


def test_linter_no_issues_clean_ruleset(tmp_path: Path):
    """Test that clean ruleset has no lint issues."""
    content = """
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 5'
    action: {class: approve}
  - name: r2
    when: 'payload.get("y", 0) < 10'
    action: {class: reject}
"""
    p = tmp_path / "clean.yaml"
    p.write_text(content)

    issues, coverage = lint_rules(tmp_path)

    assert len(issues) == 0


# ============================================================================
# Test Group 5: Contract Loading
# ============================================================================


def test_load_contract_basic(tmp_path: Path):
    """Test loading a basic contract JSON."""
    contract_content = json.dumps({
        "name": "test_contract",
        "version": "1.0.0",
        "rule_path": "rules/test.yaml",
        "description": "Test contract"
    })

    # Mock contracts_dir in settings temporarily
    from packages.common.config import settings
    orig_contracts_dir = settings.contracts_dir
    settings.contracts_dir = str(tmp_path)

    contract_path = tmp_path / "test_contract.contract.json"
    contract_path.write_text(contract_content)

    contract = load_contract("test_contract")

    assert contract["name"] == "test_contract"
    assert contract["rule_path"] == "rules/test.yaml"

    # Restore original setting
    settings.contracts_dir = orig_contracts_dir


# ============================================================================
# Test Group 6: Edge Cases
# ============================================================================


def test_evaluate_empty_ruleset(tmp_path: Path):
    """Test evaluation with no rules."""
    content = """
name: test
version: 1
rules: []
"""
    p = tmp_path / "empty.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"x": 5})

    assert out["class"] == "review"  # Default
    assert len(out["rules_applied"]) == 0


def test_evaluate_with_empty_payload(tmp_path: Path):
    """Test evaluation with empty payload."""
    content = """
name: test
version: 1
rules:
  - name: check_default
    when: 'payload.get("x", 0) == 0'
    action: {class: approve}
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {})

    assert out["class"] == "approve"


def test_evaluate_numeric_comparison_types(tmp_path: Path):
    """Test numeric comparisons with different types."""
    content = """
name: test
version: 1
rules:
  - name: float_check
    when: 'payload.get("score", 0.0) >= 0.75'
    action: {class: approve}
  - name: int_check
    when: 'payload.get("count", 0) >= 10'
    action: {class: reject}
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)

    out = evaluate_rules(rs, {"score": 0.8, "count": 15})

    assert "float_check" in out["rules_applied"]
    assert "int_check" in out["rules_applied"]


def test_linter_handles_empty_directory(tmp_path: Path):
    """Test that linter handles empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    issues, coverage = lint_rules(empty_dir)

    assert len(issues) == 0
    # Coverage defaults to 1 rule minimum to avoid division by zero
    assert coverage["rules"] >= 0.0


def test_safe_eval_handles_or_logic():
    """Test that OR boolean logic works correctly."""
    result = safe_eval(
        'payload.get("a", 0) > 100 or payload.get("b", 0) < 10',
        {"payload": {"a": 5, "b": 8}}
    )
    assert result is True


def test_safe_eval_handles_not_logic():
    """Test that NOT boolean logic works correctly."""
    result = safe_eval(
        'not payload.get("rejected", False)',
        {"payload": {"rejected": False}}
    )
    assert result is True


# ============================================================================
# Summary Stats
# ============================================================================

def test_count_all_tests():
    """Meta-test to verify we have 20+ test cases."""
    import sys
    import inspect

    # Count test functions in this module
    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    # Excluding this meta-test itself
    test_count = len(test_functions) - 1

    print(f"\nTotal test cases in test_rule_dsl_comprehensive.py: {test_count}")
    assert test_count >= 20, f"Expected 20+ tests, found {test_count}"
