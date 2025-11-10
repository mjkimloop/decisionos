from pathlib import Path
from fastapi.testclient import TestClient
from apps.gateway.main import app
from apps.executor.pipeline import decide
from apps.executor.hooks.checklist import required_docs_hook
from apps.rule_engine.engine import RuleSet, evaluate_rules
from apps.rule_engine.linter import lint_rules


def test_gateway_simulate_endpoint():
    client = TestClient(app)
    payload = {"rows": [{"org_id": "a", "credit_score": 540, "dti": 0.7, "income_verified": True}], "label_key": "converted"}
    r = client.post("/api/v1/simulate/lead_triage", json=payload, headers={"Authorization": "Bearer secret-token"})
    assert r.status_code == 200
    m = r.json()["metrics"]
    assert set(m.keys()) == {"reject_precision", "reject_recall", "review_rate"}


def test_pipeline_decide_review_checklist():
    res = decide("lead_triage", "orgA", {"credit_score": 620, "dti": 0.5, "income_verified": False})
    assert res["class"] in {"review", "reject", "approve"}
    if res["class"] == "review":
        assert set(res["required_docs"]) >= {"identity", "income_proof"}


def test_required_docs_hook_adds_for_review():
    out = required_docs_hook({"class": "review", "required_docs": ["x"]})
    assert set(out) >= {"x", "identity", "income_proof"}


def test_arithmetic_in_when(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: r
    when: 'payload.get("a", 0) + 2 > 3'
    action: {class: approve}
"""
    f = tmp_path / "r.yaml"
    f.write_text(content)
    rs = RuleSet.load(f)
    out = evaluate_rules(rs, {"a": 2})
    assert out["class"] == "approve"


def test_multiple_rule_merge(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: r1
    when: 'payload.get("a", 0) > 0'
    action: {class: review, reasons: ["r1"], required_docs: ["d1"]}
  - name: r2
    when: 'payload.get("b", 0) > 0'
    action: {reasons: ["r2"], required_docs: ["d2"]}
"""
    f = tmp_path / "r.yaml"
    f.write_text(content)
    rs = RuleSet.load(f)
    out = evaluate_rules(rs, {"a": 1, "b": 1})
    assert set(out["reasons"]) == {"r1", "r2"}
    assert set(out["required_docs"]) == {"d1", "d2"}


def test_linter_coverage_numbers(tmp_path: Path):
    content = """
name: t
version: 1
rules:
  - name: a
    when: 'payload.get("x", 0) > 0'
    priority: 1
    stop: true
    action: {class: reject}
"""
    p = tmp_path / "a.yaml"
    p.write_text(content)
    _, cov = lint_rules(tmp_path)
    assert cov["priority_pct"] >= 100.0
    assert cov["stop_pct"] >= 100.0
    assert cov["action_class_pct"] >= 100.0

