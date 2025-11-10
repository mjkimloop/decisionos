from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from apps.executor import pipeline as pl
from apps.audit_ledger.ledger import AuditLedger
from apps.executor.exceptions import DomainError


GOOD: Dict[str, Any] = {"credit_score": 720, "dti": 0.3, "income_verified": True}


def test_explain_roundtrip():
    res = pl.decide("lead_triage", "orgA", GOOD)
    ex = pl.explain(res["decision_id"])  # type: ignore[index]
    assert set(ex.keys()) >= {"rules_applied", "model_meta", "input_hash", "output_hash", "timestamp"}


def test_explain_404():
    with pytest.raises(KeyError):
        pl.explain("00000000-0000-0000-0000-000000000000")


def test_budgets_reflected_in_meta():
    res = pl.decide("lead_triage", "orgA", GOOD, budgets={"latency": 50.0, "cost": 0.1})
    assert res["model_meta"]["budgets"]["latency"] == 50.0
    assert res["model_meta"]["budgets"]["cost"] == 0.1


def test_rules_only_does_not_invoke_model(monkeypatch):
    called = {"n": 0}

    def fake_invoke(meta, payload):
        called["n"] += 1

    def fake_route(contract, budgets=None):
        return {"chosen_model": "rules-only"}

    monkeypatch.setattr(pl, "_invoke_model", fake_invoke)
    monkeypatch.setattr(pl, "choose_route", fake_route)
    pl.decide("lead_triage", "orgA", GOOD)
    assert called["n"] == 0


def test_model_success_sets_invoked_not_degraded(monkeypatch):
    def fake_invoke(meta, payload):
        meta["invoked"] = True

    def fake_route(contract, budgets=None):
        return {"chosen_model": "external"}

    monkeypatch.setattr(pl, "_invoke_model", fake_invoke)
    monkeypatch.setattr(pl, "choose_route", fake_route)
    res = pl.decide("lead_triage", "orgA", GOOD)
    assert res["model_meta"].get("invoked") is True
    assert res["model_meta"].get("degraded") is not True


def test_audit_chain(tmp_path: Path, monkeypatch):
    ledger_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(pl, "_LEDGER", AuditLedger(ledger_path))
    a = pl.decide("lead_triage", "a", GOOD)
    b = pl.decide("lead_triage", "b", GOOD)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    import json

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["curr_hash"] == second["prev_hash"]


def test_simulate_no_label_range():
    rows = [{"org_id": "a", **GOOD}, {"org_id": "b", **GOOD}]
    out = pl.simulate("lead_triage", rows, None)
    assert 0.0 <= out["metrics"]["review_rate"] <= 1.0


def test_payload_validation_error_contains_field():
    bad = {"credit_score": 700, "dti": 0.3}  # missing income_verified
    with pytest.raises(DomainError) as ei:
        pl.decide("lead_triage", "orgA", bad)
    assert "income_verified" in str(ei.value)


def test_contract_schema_missing_raises_500(monkeypatch):
    def fake_load_contract(name: str):
        return {"input_schema": "schemas/does_not_exist.json"}

    monkeypatch.setattr(pl, "load_contract", fake_load_contract)
    with pytest.raises(DomainError) as ei:
        pl.decide("lead_triage", "orgA", GOOD)
    assert ei.value.status_code == 500


def test_required_docs_hook_not_added_for_approve():
    res = pl.decide("lead_triage", "orgA", {"credit_score": 720, "dti": 0.3, "income_verified": True})
    assert "identity" not in set(res["required_docs"])  # type: ignore[index]

