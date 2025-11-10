from pathlib import Path
from apps.rule_engine.parser import parse_ruleset, parse_expression


def test_parse_ruleset_loads_yaml(tmp_path: Path):
    y = tmp_path / "r.yaml"
    y.write_text(
        """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("x",0) > 5'
    priority: 5
    stop: true
    action: {class: approve, reasons: ["x_gt_5"]}
        """,
        encoding="utf-8",
    )
    rs = parse_ruleset(y)
    assert rs.rules[0].name == "r1"


def test_parse_expression_ast_guard():
    parse_expression('payload.get("x",0) > 1')

