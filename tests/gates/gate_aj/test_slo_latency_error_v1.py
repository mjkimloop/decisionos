"""
tests/gates/gate_aj/test_slo_latency_error_v1.py

Gate-AJ: SLO latency/error 정책 테스트
"""
import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.slo_judge import evaluate


def _ev_with_perf(p95=900, p99=1800, error_rate=0.01):
    """perf 포함 Evidence 생성"""
    return {
        "meta": {"version": "v0.5.11h"},
        "witness": {"csv_sha256": "abc123", "rows": 1000},
        "usage": {"buckets": {}, "deltas_by_metric": {}},
        "rating": {"subtotal": 0.3, "items": []},
        "quota": {"decisions": {}},
        "budget": {"level": "ok", "spent": 0.3, "limit": 1.0},
        "anomaly": {"is_spike": False, "ewma": 0.12, "ratio": 0.5},
        "perf": {
            "latency_ms": {"p50": 320, "p95": p95, "p99": p99},
            "error_rate": error_rate,
            "count": 1000,
            "window": {"start": "2025-01-01T10:00:00", "end": "2025-01-01T10:10:00"},
        },
        "integrity": {"signature_sha256": "dummy"},
    }


def _slo_with_perf(max_p95=1200, max_p99=2500, max_error_rate=0.02):
    """perf 정책 포함 SLO 생성"""
    return {
        "version": "v1",
        "budget": {"allow_levels": ["ok", "warn"], "max_spent": 1.0},
        "quota": {"forbid_actions": {}},
        "anomaly": {"allow_spike": False},
        "latency": {"max_p95_ms": max_p95, "max_p99_ms": max_p99},
        "error": {"max_error_rate": max_error_rate},
        "witness": {
            "require_csv_sha256": True,
            "require_signature": False,
            "min_rows": 1,
        },
        "integrity": {"require_signature": False},
        "quorum": {"k": 2, "n": 3, "fail_closed_on_degrade": True},
    }


def test_perf_ok_pass():
    """perf OK → pass"""
    ev = _ev_with_perf(p95=900, p99=1800, error_rate=0.01)
    slo = _slo_with_perf(max_p95=1200, max_p99=2500, max_error_rate=0.02)
    dec, reasons = evaluate(ev, slo)
    assert dec == "pass" and reasons == []


def test_perf_p95_over_fail():
    """p95 초과 → fail"""
    ev = _ev_with_perf(p95=1300, p99=1800, error_rate=0.01)
    slo = _slo_with_perf(max_p95=1200, max_p99=2500, max_error_rate=0.02)
    dec, reasons = evaluate(ev, slo)
    assert dec == "fail"
    assert any(r.startswith("latency.p95_over") for r in reasons)


def test_perf_p99_over_fail():
    """p99 초과 → fail"""
    ev = _ev_with_perf(p95=900, p99=2600, error_rate=0.01)
    slo = _slo_with_perf(max_p95=1200, max_p99=2500, max_error_rate=0.02)
    dec, reasons = evaluate(ev, slo)
    assert dec == "fail"
    assert any(r.startswith("latency.p99_over") for r in reasons)


def test_perf_error_rate_over_fail():
    """error_rate 초과 → fail"""
    ev = _ev_with_perf(p95=900, p99=1800, error_rate=0.03)
    slo = _slo_with_perf(max_p95=1200, max_p99=2500, max_error_rate=0.02)
    dec, reasons = evaluate(ev, slo)
    assert dec == "fail"
    assert any(r.startswith("error.rate_over") for r in reasons)


def test_perf_missing_fail():
    """perf 누락 (latency 정책 존재) → fail"""
    ev = _ev_with_perf()
    del ev["perf"]  # perf 제거
    slo = _slo_with_perf(max_p95=1200, max_p99=2500, max_error_rate=0.02)
    dec, reasons = evaluate(ev, slo)
    assert dec == "fail"
    assert "perf.missing" in reasons


def test_no_perf_policy_no_check():
    """perf 정책 없으면 perf 검증 안 함"""
    ev = _ev_with_perf()
    del ev["perf"]  # perf 제거
    slo = _slo_with_perf(max_p95=None, max_p99=None, max_error_rate=None)
    dec, reasons = evaluate(ev, slo)
    assert dec == "pass"  # perf 없어도 통과
