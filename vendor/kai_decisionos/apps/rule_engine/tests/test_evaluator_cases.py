import pytest
from apps.rule_engine.parser import parse_ruleset
from apps.rule_engine.evaluator import evaluate_rules
from pathlib import Path


@pytest.fixture()
def rs(tmp_path: Path):
    y = tmp_path / "r.yaml"
    y.write_text(
        """
name: t
version: 1
rules:
  - name: strong
    when: 'payload.get("credit_score",0) >= 700 and payload.get("dti",1.0) <= 0.35'
    priority: 10
    stop: true
    action: {class: approve, reasons: ["strong"], confidence: 0.9}
  - name: weak
    when: 'payload.get("credit_score",0) < 550 or payload.get("dti",0) > 0.6'
    priority: 9
    stop: true
    action: {class: reject, reasons: ["weak"], confidence: 0.9}
  - name: review
    when: 'payload.get("income_verified") == False'
    priority: 5
    action: {class: review, reasons: ["docs"], required_docs: ["income_proof"]}
        """,
        encoding="utf-8",
    )
    return parse_ruleset(y)


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"credit_score": 720, "dti": 0.3, "income_verified": True}, "approve"),
        ({"credit_score": 540, "dti": 0.4, "income_verified": True}, "reject"),
        ({"credit_score": 640, "dti": 0.5, "income_verified": False}, "review"),
        ({"credit_score": 680, "dti": 0.42, "income_verified": True}, "review"),
        ({"credit_score": 600, "dti": 0.61, "income_verified": True}, "reject"),
    ],
)
def test_various_decisions(rs, payload, expected):
    out = evaluate_rules(rs, payload)
    assert out["class"] == expected


@pytest.mark.parametrize("cs", [700, 710, 800, 900, 1000])
def test_approve_priority(rs, cs):
    out = evaluate_rules(rs, {"credit_score": cs, "dti": 0.3, "income_verified": True})
    assert out["class"] == "approve"

