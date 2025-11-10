import hashlib
import json

import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.slo_judge import evaluate


def _canary_block(p95_rel=0.1, error_delta=0.001, sig_delta=0.0001, canary_count=2000):
    return {
        "control_perf": {"p95": 100, "error_rate": 0.01, "count": 2000},
        "canary_perf": {"p95": 110, "error_rate": 0.011, "count": canary_count},
        "deltas": {
            "p95_rel": p95_rel,
            "error_delta": error_delta,
            "sig_error_delta": sig_delta,
        },
    }


def _evidence(canary_block):
    base = {
        "meta": {"tenant": "demo"},
        "witness": {"csv_sha256": "abc"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok"},
        "anomaly": {"is_spike": False},
        "perf": {"latency_ms": {"p95": 100, "p99": 110}, "error_rate": 0.01},
        "perf_judge": None,
        "canary": canary_block,
    }
    core = {k: base[k] for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
    for optional in ("perf", "perf_judge", "judges", "canary"):
        if base.get(optional) is not None:
            core[optional] = base[optional]
    base["integrity"] = {
        "signature_sha256": hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    }
    return base


SLO = {
    "canary": {
        "thresholds": {
            "max_p95_rel_increase": 0.15,
            "max_error_abs_delta": 0.01,
            "max_sig_error_delta": 0.0005,
        },
        "min_sample_count": 1000,
        "guardband_minutes": 10,
    }
}


def test_canary_slo_pass():
    decision, reasons = evaluate(_evidence(_canary_block()), SLO)
    assert decision == "pass", reasons
    assert reasons == []


def test_canary_slo_fail_rel():
    decision, reasons = evaluate(_evidence(_canary_block(p95_rel=0.2)), SLO)
    assert decision == "fail"
    assert any("canary.p95_rel_over" in r for r in reasons)


def test_canary_sample_insufficient():
    decision, reasons = evaluate(_evidence(_canary_block(canary_count=100)), SLO)
    assert decision == "fail"
    assert "canary.sample_insufficient" in reasons
