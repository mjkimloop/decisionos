"""
tests/gates/gate_aj/test_slo_local_and_quorum_v1.py

Gate-AJ: SLO 판정 및 멀티-저지 쿼럼 테스트
"""
import json
import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.slo_judge import evaluate
from apps.judge.quorum import decide


def _ev_ok():
    """정상 Evidence 샘플"""
    return {
        "meta": {"version": "v0.5.11f"},
        "witness": {"csv_sha256": "abc123", "rows": 3},
        "usage": {"buckets": {}, "deltas_by_metric": {"tokens": 130.0}},
        "rating": {"subtotal": 0.6, "items": []},
        "quota": {
            "decisions": {
                "tokens": {"action": "allow", "used": 110, "soft": 100, "hard": 120}
            }
        },
        "budget": {"level": "ok", "spent": 0.3, "limit": 1.0},
        "anomaly": {"is_spike": False, "ewma": 0.12, "ratio": 0.5},
        "integrity": {"signature_sha256": "dummy"},  # 테스트에선 검증 off
    }


def _slo_canary():
    """Canary SLO 정책 (관대)"""
    return {
        "version": "v1",
        "budget": {"allow_levels": ["ok", "warn"], "max_spent": 1.0},
        "quota": {"forbid_actions": {"tokens": ["deny"]}},
        "anomaly": {"allow_spike": False},
        "witness": {
            "require_csv_sha256": True,
            "require_signature": False,
            "min_rows": 1,
        },
        "integrity": {"require_signature": False},
        "quorum": {"k": 2, "n": 3, "fail_closed_on_degrade": True},
    }


def test_local_judge_pass_canary():
    """단일 Judge: 정상 케이스 → pass"""
    ev = _ev_ok()
    slo = _slo_canary()
    dec, reasons = evaluate(ev, slo)
    assert dec == "pass" and reasons == []


def test_local_judge_fail_budget_quota():
    """단일 Judge: budget/quota 위반 → fail"""
    ev = _ev_ok()
    ev["budget"]["level"] = "exceeded"
    ev["quota"]["decisions"]["tokens"]["action"] = "deny"
    slo = _slo_canary()
    dec, reasons = evaluate(ev, slo)
    assert dec == "fail"
    assert any(r.startswith("budget.level_forbidden") for r in reasons)
    assert any(r.startswith("quota.forbid") for r in reasons)


def test_quorum_2_of_3_pass():
    """쿼럼: 2/3 pass → final pass"""
    ev = _ev_ok()
    slo = _slo_canary()

    def p_pass(e, s):
        return ("pass", [])

    def p_fail(e, s):
        return ("fail", ["x"])

    res = decide([p_pass, p_pass, p_fail], ev, slo, k=2, n=3)
    assert res["final"] == "pass" and res["pass_count"] == 2


def test_quorum_1_of_3_fail():
    """쿼럼: 1/3 pass → final fail"""
    ev = _ev_ok()
    slo = _slo_canary()

    def p_pass(e, s):
        return ("pass", [])

    def p_fail(e, s):
        return ("fail", ["x"])

    res = decide([p_pass, p_fail, p_fail], ev, slo, k=2, n=3)
    assert res["final"] == "fail" and res["pass_count"] == 1


def test_missing_evidence_keys():
    """필수 키 누락 → fail"""
    ev = {"meta": {}, "witness": {}}  # 나머지 키 누락
    slo = _slo_canary()
    dec, reasons = evaluate(ev, slo)
    assert dec == "fail"
    assert any("evidence.missing" in r for r in reasons)
