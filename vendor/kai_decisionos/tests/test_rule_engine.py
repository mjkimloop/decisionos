from apps.rule_engine.engine import RuleSet, evaluate_rules


def test_evaluate_rules_basic(tmp_path):
    content = """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 5'
    action:
      class: approve
      reasons: ["x_gt_5"]
      confidence: 0.8
"""
    p = tmp_path / "r.yaml"
    p.write_text(content)
    rs = RuleSet.load(p)
    out = evaluate_rules(rs, {"x": 10})
    assert out["class"] == "approve"
    assert "x_gt_5" in out["reasons"]
