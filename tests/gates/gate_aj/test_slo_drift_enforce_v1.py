import pytest
import json

pytestmark = [pytest.mark.gate_aj]


def test_drift_severity_forbidden(tmp_path):
    """Drift severity가 forbidden 목록에 있으면 fail"""
    from apps.judge.slo_schema import SLOSpec
    from apps.judge.slo_judge import evaluate

    # drift JSON 준비
    drift_path = tmp_path / "posterior_drift.json"
    drift_path.write_text(json.dumps({
        "severity": "critical",
        "abs_diff": 0.2,
        "kl": 1.5,
        "reason_codes": ["abs_diff_critical"]
    }), encoding="utf-8")

    # SLO 설정
    slo = {
        "version": "v1",
        "drift": {
            "source": str(drift_path),
            "max_abs_diff": 0.12,
            "max_kl": 1.2,
            "forbid_severity": ["critical"]
        }
    }

    # Evidence (최소한의 필수 블록)
    evidence = {
        "meta": {},
        "witness": {"csv_sha256": "abc123"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok"},
        "anomaly": {},
        "integrity": {"signature_sha256": "def456"}
    }

    spec = SLOSpec(**slo)
    decision, reasons = evaluate(evidence, slo)

    assert decision == "fail"
    assert any("drift.severity_forbidden" in r for r in reasons)


def test_drift_abs_diff_over(tmp_path):
    """abs_diff가 max를 초과하면 fail"""
    from apps.judge.slo_judge import evaluate

    drift_path = tmp_path / "posterior_drift.json"
    drift_path.write_text(json.dumps({
        "severity": "warn",
        "abs_diff": 0.20,  # max 0.12 초과
        "kl": 0.5
    }), encoding="utf-8")

    slo = {
        "version": "v1",
        "drift": {
            "source": str(drift_path),
            "max_abs_diff": 0.12,
            "max_kl": 1.2,
            "forbid_severity": ["critical"]
        }
    }

    evidence = {
        "meta": {},
        "witness": {"csv_sha256": "abc123"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok"},
        "anomaly": {},
        "integrity": {"signature_sha256": "def456"}
    }

    decision, reasons = evaluate(evidence, slo)

    assert decision == "fail"
    assert any("drift.abs_over" in r for r in reasons)


def test_drift_kl_over(tmp_path):
    """KL divergence가 max를 초과하면 fail"""
    from apps.judge.slo_judge import evaluate

    drift_path = tmp_path / "posterior_drift.json"
    drift_path.write_text(json.dumps({
        "severity": "info",
        "abs_diff": 0.05,
        "kl": 2.0  # max 1.2 초과
    }), encoding="utf-8")

    slo = {
        "version": "v1",
        "drift": {
            "source": str(drift_path),
            "max_abs_diff": 0.12,
            "max_kl": 1.2,
            "forbid_severity": ["critical"]
        }
    }

    evidence = {
        "meta": {},
        "witness": {"csv_sha256": "abc123"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok"},
        "anomaly": {},
        "integrity": {"signature_sha256": "def456"}
    }

    decision, reasons = evaluate(evidence, slo)

    assert decision == "fail"
    assert any("drift.kl_over" in r for r in reasons)


def test_drift_pass(tmp_path):
    """모든 조건 통과 시 pass"""
    from apps.judge.slo_judge import evaluate

    drift_path = tmp_path / "posterior_drift.json"
    drift_path.write_text(json.dumps({
        "severity": "info",
        "abs_diff": 0.05,
        "kl": 0.8
    }), encoding="utf-8")

    slo = {
        "version": "v1",
        "integrity": {
            "require_signature": False
        },
        "witness": {
            "require_csv_sha256": False
        },
        "drift": {
            "source": str(drift_path),
            "max_abs_diff": 0.12,
            "max_kl": 1.2,
            "forbid_severity": ["critical"]
        }
    }

    evidence = {
        "meta": {},
        "witness": {"csv_sha256": "abc123"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok"},
        "anomaly": {},
        "integrity": {"signature_sha256": "def456"}
    }

    decision, reasons = evaluate(evidence, slo)

    # Debug: 실패 원인 확인
    if decision != "pass":
        print(f"Expected pass but got {decision}, reasons: {reasons}")

    assert decision == "pass", f"Expected pass but got {decision}, reasons: {reasons}"
    assert not any("drift." in r for r in reasons)
