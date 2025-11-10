from __future__ import annotations

import time
from typing import Any, Dict

import pytest

from apps.executor.pipeline import decide, simulate
from apps.executor import pipeline as pl
from apps.executor.exceptions import DomainError


GOOD_PAYLOAD: Dict[str, Any] = {"credit_score": 720, "dti": 0.3, "income_verified": True}


def test_decide_validates_contract_and_returns_result():
    res = decide("lead_triage", "orgA", GOOD_PAYLOAD)
    assert res["decision_id"] and res["class"] in {"approve", "review", "reject"}


def test_decide_invalid_payload_raises_domain_error():
    bad = {"credit_score": 720, "dti": 0.3}  # missing income_verified
    with pytest.raises(DomainError) as ei:
        decide("lead_triage", "orgA", bad)
    assert ei.value.status_code == 400


def test_missing_contract_raises_404():
    with pytest.raises(DomainError) as ei:
        decide("does_not_exist", "orgA", GOOD_PAYLOAD)
    assert ei.value.status_code == 404


def test_latency_under_200ms_average():
    start = time.perf_counter()
    n = 20
    for _ in range(n):
        decide("lead_triage", "orgA", GOOD_PAYLOAD)
    dur_ms = (time.perf_counter() - start) * 1000 / n
    assert dur_ms < 200.0


def test_degrade_on_model_failure(monkeypatch):
    def fake_choose_route(contract: str, budgets: dict | None = None):
        return {"chosen_model": "external"}

    def failing_model(meta, payload):
        raise RuntimeError("boom")

    monkeypatch.setattr(pl, "choose_route", fake_choose_route)
    monkeypatch.setattr(pl, "_invoke_model", failing_model)
    res = decide("lead_triage", "orgA", GOOD_PAYLOAD)
    assert res["model_meta"].get("degraded") is True
    assert res["class"] in {"approve", "review", "reject"}


def test_simulate_metrics_contract_validation():
    rows = [
        {"org_id": "a", **GOOD_PAYLOAD, "converted": 1},
        {"org_id": "b", **GOOD_PAYLOAD, "converted": 0},
    ]
    out = simulate("lead_triage", rows, "converted")
    assert set(out["metrics"]) == {"reject_precision", "reject_recall", "review_rate"}
