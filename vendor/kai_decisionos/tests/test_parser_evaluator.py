"""
Tests for parser.py and evaluator.py modules

Focuses on error handling, edge cases, and uncovered code paths
to increase coverage to ≥70%.
"""
import pytest
from pathlib import Path
import tempfile

from apps.rule_engine.parser import Rule, RuleSet, load_ruleset
from apps.rule_engine.evaluator import (
    safe_eval,
    evaluate_rule,
    evaluate_rules,
    introspect_expression,
    ALLOWED_AST_NODES,
)


# ============================================================================
# Parser Tests
# ============================================================================


def test_rule_validation_missing_name():
    """Rule must have a name"""
    with pytest.raises(ValueError, match="must have a name"):
        Rule(name="", when="True", action={"class": "approve"})


def test_rule_validation_missing_when():
    """Rule must have a when condition"""
    with pytest.raises(ValueError, match="must have a 'when' condition"):
        Rule(name="test", when="", action={"class": "approve"})


def test_rule_validation_invalid_action_type():
    """Rule action must be a dict"""
    with pytest.raises(ValueError, match="action must be a dict"):
        Rule(name="test", when="True", action="not_a_dict")  # type: ignore


def test_rule_validation_missing_action_class():
    """Rule action must have a 'class' field"""
    with pytest.raises(ValueError, match="action must have a 'class' field"):
        Rule(name="test", when="True", action={"reasons": []})


def test_ruleset_load_file_not_found():
    """RuleSet.load raises FileNotFoundError for missing file"""
    with pytest.raises(FileNotFoundError, match="not found"):
        RuleSet.load("nonexistent_file.yaml")


def test_ruleset_load_invalid_yaml():
    """RuleSet.load raises ValueError for malformed YAML"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("{ invalid yaml: [}")
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Invalid YAML"):
            RuleSet.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_ruleset_load_yaml_not_dict():
    """RuleSet.load raises ValueError if YAML root is not a dict"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("- item1\n- item2\n")
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="YAML root must be a dict"):
            RuleSet.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_ruleset_load_rules_not_list():
    """RuleSet.load raises ValueError if 'rules' is not a list"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("name: test\nrules: not_a_list\n")
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="'rules' must be a list"):
            RuleSet.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_ruleset_load_rule_not_dict():
    """RuleSet.load raises ValueError if rule is not a dict"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("name: test\nrules:\n  - not_a_dict_string\n")
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="must be a dict"):
            RuleSet.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_ruleset_load_rule_invalid_structure():
    """RuleSet.load raises ValueError if rule structure is invalid"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("name: test\nrules:\n  - name: r1\n    action: {}\n")  # Missing 'when'
        f.flush()
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="invalid structure"):
            RuleSet.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_ruleset_get_rule_found():
    """RuleSet.get_rule returns rule by name"""
    rule1 = Rule(name="r1", when="True", action={"class": "approve"})
    rule2 = Rule(name="r2", when="False", action={"class": "reject"})
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1, rule2])

    assert ruleset.get_rule("r1") == rule1
    assert ruleset.get_rule("r2") == rule2


def test_ruleset_get_rule_not_found():
    """RuleSet.get_rule returns None for missing rule"""
    rule1 = Rule(name="r1", when="True", action={"class": "approve"})
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1])

    assert ruleset.get_rule("nonexistent") is None


def test_ruleset_get_rules_by_priority():
    """RuleSet.get_rules_by_priority returns rules sorted descending"""
    rule1 = Rule(name="r1", when="True", action={"class": "approve"}, priority=10)
    rule2 = Rule(name="r2", when="True", action={"class": "reject"}, priority=50)
    rule3 = Rule(name="r3", when="True", action={"class": "review"}, priority=30)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1, rule2, rule3])

    sorted_rules = ruleset.get_rules_by_priority()
    assert [r.name for r in sorted_rules] == ["r2", "r3", "r1"]


# ============================================================================
# Evaluator Tests
# ============================================================================


def test_safe_eval_syntax_error():
    """safe_eval raises SyntaxError for malformed expression"""
    with pytest.raises(SyntaxError, match="Invalid expression syntax"):
        safe_eval("this is not valid python (", {"payload": {}})


def test_safe_eval_disallowed_import():
    """safe_eval blocks import statements"""
    with pytest.raises(ValueError, match="Only attribute method calls allowed"):
        safe_eval("__import__('os')", {"payload": {}})


def test_safe_eval_disallowed_attribute():
    """safe_eval blocks attribute access except payload.get"""
    with pytest.raises(ValueError, match="Only payload.get\\(\\) calls allowed"):
        safe_eval("payload.keys()", {"payload": {}})


def test_safe_eval_disallowed_function_call():
    """safe_eval blocks function calls except payload.get"""
    with pytest.raises(ValueError, match="Only attribute method calls allowed"):
        safe_eval("len(payload)", {"payload": {}})


def test_safe_eval_disallowed_keyword_args():
    """safe_eval blocks keyword arguments in payload.get"""
    with pytest.raises(ValueError, match="Keyword arguments not allowed"):
        safe_eval("payload.get(key='value')", {"payload": {}})


def test_safe_eval_disallowed_non_constant_args():
    """safe_eval blocks non-constant arguments in payload.get"""
    with pytest.raises(ValueError, match="must be constants"):
        safe_eval("payload.get(some_var)", {"payload": {}})


def test_safe_eval_evaluation_error():
    """safe_eval wraps evaluation errors"""
    with pytest.raises(ValueError, match="Evaluation error"):
        safe_eval("1 / 0", {"payload": {}})


def test_evaluate_rule_success():
    """evaluate_rule evaluates rule condition successfully"""
    rule = Rule(name="test", when="payload.get('score', 0) > 50", action={"class": "approve"})
    assert evaluate_rule(rule, {"score": 60}) is True
    assert evaluate_rule(rule, {"score": 40}) is False


def test_evaluate_rule_error():
    """evaluate_rule raises ValueError on evaluation error"""
    rule = Rule(name="test", when="invalid syntax (", action={"class": "approve"})
    with pytest.raises(ValueError, match="Failed to evaluate rule"):
        evaluate_rule(rule, {})


def test_evaluate_rules_stop_flag():
    """evaluate_rules stops at first matching rule with stop=True"""
    rule1 = Rule(name="r1", when="True", action={"class": "approve", "reasons": ["r1"]}, priority=100, stop=True)
    rule2 = Rule(name="r2", when="True", action={"class": "reject", "reasons": ["r2"]}, priority=50)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1, rule2])

    result = evaluate_rules(ruleset, {})
    assert result["class"] == "approve"
    assert "r1" in result["reasons"]
    assert "r2" not in result["reasons"]
    assert len(result["rules_applied"]) == 1


def test_evaluate_rules_merge_reasons():
    """evaluate_rules merges reasons from multiple matching rules"""
    rule1 = Rule(name="r1", when="True", action={"class": "review", "reasons": ["r1"]}, priority=100)
    rule2 = Rule(name="r2", when="True", action={"class": "review", "reasons": ["r2", "r1"]}, priority=50)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1, rule2])

    result = evaluate_rules(ruleset, {})
    assert set(result["reasons"]) == {"r1", "r2"}


def test_evaluate_rules_merge_required_docs():
    """evaluate_rules merges required_docs from multiple rules"""
    rule1 = Rule(name="r1", when="True", action={"class": "review", "required_docs": ["doc1"]}, priority=100)
    rule2 = Rule(name="r2", when="True", action={"class": "review", "required_docs": ["doc2"]}, priority=50)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1, rule2])

    result = evaluate_rules(ruleset, {})
    assert set(result["required_docs"]) == {"doc1", "doc2"}


def test_evaluate_rules_override_class():
    """evaluate_rules overrides class with later matching rule (no stop)"""
    rule1 = Rule(name="r1", when="True", action={"class": "approve"}, priority=100)
    rule2 = Rule(name="r2", when="True", action={"class": "reject"}, priority=50)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1, rule2])

    result = evaluate_rules(ruleset, {})
    # Last matching rule without stop overrides
    assert result["class"] == "reject"


def test_evaluate_rules_default_outcome():
    """evaluate_rules returns default outcome when no rules match"""
    rule1 = Rule(name="r1", when="False", action={"class": "approve"}, priority=100)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1])

    result = evaluate_rules(ruleset, {})
    assert result["class"] == "review"  # default
    assert result["confidence"] == 0.5
    assert result["reasons"] == []
    assert result["rules_applied"] == []


def test_evaluate_rules_error_in_rule():
    """evaluate_rules records error in rules_applied"""
    rule1 = Rule(name="r1", when="payload.bad_syntax (", action={"class": "approve"}, priority=100)
    ruleset = RuleSet(name="test", version="1.0", rules=[rule1])

    result = evaluate_rules(ruleset, {})
    assert len(result["rules_applied"]) == 1
    assert result["rules_applied"][0].startswith("ERROR:r1:")


def test_introspect_expression_valid():
    """introspect_expression analyzes valid expression"""
    result = introspect_expression("payload.get('score', 0) > 50")
    assert result["valid"] is True
    assert "Compare" in result["nodes"]
    assert result["error"] is None


def test_introspect_expression_invalid():
    """introspect_expression handles invalid syntax"""
    result = introspect_expression("invalid (")
    assert result["valid"] is False
    assert result["nodes"] == []
    assert result["error"] is not None


def test_load_ruleset_function():
    """load_ruleset convenience function works"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = load_ruleset(ruleset_path)
    assert ruleset.name == "lead_triage_rules"
    assert len(ruleset.rules) == 6


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_pipeline_with_errors():
    """Test full pipeline with various error conditions"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
name: error_test
version: 1.0.0
rules:
  - name: good_rule
    when: payload.get('valid', False)
    priority: 100
    action:
      class: approve
      reasons: ["valid"]
  - name: bad_rule
    when: "this will cause error ("
    priority: 50
    action:
      class: reject
      reasons: ["invalid"]
""")
        f.flush()
        temp_path = f.name

    try:
        ruleset = load_ruleset(temp_path)
        result = evaluate_rules(ruleset, {"valid": True})

        # good_rule should match
        assert result["class"] == "approve"
        # bad_rule should have error
        assert any("ERROR:bad_rule:" in r for r in result["rules_applied"])
    finally:
        Path(temp_path).unlink()


def test_ast_node_whitelist_complete():
    """Verify ALLOWED_AST_NODES contains expected types"""
    import ast

    expected_types = [
        ast.Expression,
        ast.BoolOp,
        ast.Compare,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Attribute,
        ast.Call,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.Gt,
    ]

    for expected in expected_types:
        assert expected in ALLOWED_AST_NODES
