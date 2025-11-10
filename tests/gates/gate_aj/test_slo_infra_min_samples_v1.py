import pytest

from apps.judge.slo_judge import evaluate

pytestmark = [pytest.mark.gate_aj]


def _base_evidence(count: int) -> dict:
    return {
        "meta": {},
        "witness": {},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok", "spent": 0},
        "anomaly": {"is_spike": False},
        "integrity": {"signature_sha256": "x"},
        "perf": {"count": count, "latency_ms": {"p95": 100, "p99": 150}, "error_rate": 0.0},
        "perf_judge": {
            "count": count,
            "latency_ms": {"p95": 100, "p99": 150},
            "availability": 1.0,
            "signature_error_rate": 0.0,
        },
    }


def _slo(min_samples: int) -> dict:
    return {
        "witness": {"require_csv_sha256": False},
        "integrity": {"require_signature": False},
        "judge_infra": {
            "latency": {"max_p95_ms": 200, "max_p99_ms": 400, "min_samples": min_samples},
            "sig": {"max_sig_error_rate": 0.01, "min_samples": min_samples},
        },
    }


def test_infra_min_samples_fail_on_insufficient():
    evidence = _base_evidence(count=10)
    decision, reasons = evaluate(evidence, _slo(min_samples=100))
    assert decision == "fail"
    assert "infra.samples_insufficient_latency" in reasons


def test_infra_min_samples_pass_when_enough():
    evidence = _base_evidence(count=200)
    decision, reasons = evaluate(evidence, _slo(min_samples=100))
    assert decision == "pass"
    assert "infra.samples_insufficient_latency" not in reasons
