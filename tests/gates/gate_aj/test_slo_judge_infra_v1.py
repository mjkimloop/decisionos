import hashlib
import json

import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.slo_judge import evaluate


def _base_evidence(perf_extra: dict | None = None):
    ev = {
        "meta": {"tenant": "demo"},
        "witness": {"csv_sha256": "abc"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok", "spent": 0.1, "limit": 1.0},
        "anomaly": {"is_spike": False},
        "perf": None,
        "perf_judge": {
            "latency_ms": {"p50": 100, "p95": 800, "p99": 1200},
            "availability": 0.999,
            "error_rate": 0.001,
            "signature_error_rate": 0.0001,
        },
        "integrity": {"signature_sha256": "placeholder"},
    }
    if perf_extra:
        ev["perf_judge"].update(perf_extra)
    core = {
        k: ev[k]
        for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]
    }
    ev["integrity"]["signature_sha256"] = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return ev


def _infra_slo():
    return {
        "judge_infra": {
            "latency": {"max_p95_ms": 900, "max_p99_ms": 1500},
            "availability": {"min_availability": 0.99},
            "sig": {"max_sig_error_rate": 0.001},
        }
    }


def test_infra_slo_passes():
    decision, reasons = evaluate(_base_evidence(), _infra_slo())
    assert decision == "pass"
    assert reasons == []


def test_infra_latency_fail():
    ev = _base_evidence({"latency_ms": {"p50": 100, "p95": 950, "p99": 2000}})
    decision, reasons = evaluate(ev, _infra_slo())
    assert decision == "fail"
    assert any("infra.latency_p95_over" in r for r in reasons)
    assert any("infra.latency_p99_over" in r for r in reasons)


def test_infra_availability_fail():
    ev = _base_evidence({"availability": 0.9})
    decision, reasons = evaluate(ev, _infra_slo())
    assert decision == "fail"
    assert any("infra.availability_low" in r for r in reasons)


def test_infra_sig_fail():
    ev = _base_evidence({"signature_error_rate": 0.01})
    decision, reasons = evaluate(ev, _infra_slo())
    assert decision == "fail"
    assert any("infra.sig_error_rate_over" in r for r in reasons)


def test_infra_missing_perf_block():
    ev = _base_evidence()
    del ev["perf_judge"]
    decision, reasons = evaluate(ev, _infra_slo())
    assert decision == "fail"
    assert "infra.perf_missing" in reasons
