"""
Test Risk Governor Mapping v1
다양한 신호 조합 → risk_score/액션 검증
"""
import pytest
from apps.rollout.risk.governor import RiskGovernor, GovernorConfig


@pytest.mark.gate_u
def test_low_risk_promote():
    """모든 신호 정상 → risk<0.3 → promote"""
    config = {
        "weights": {
            "drift_z": 0.35,
            "anomaly_score": 0.20,
            "infra_p95_ms": 0.15,
            "error_rate": 0.15,
            "quota_denies": 0.10,
            "budget_level": 0.05
        },
        "norm": {
            "drift_z": {"type": "zscore", "cap": 5.0},
            "anomaly_score": {"type": "linear", "min": 0, "max": 1},
            "infra_p95_ms": {"type": "minmax", "min": 300, "max": 2000},
            "error_rate": {"type": "minmax", "min": 0.0, "max": 0.05},
            "quota_denies": {"type": "minmax", "min": 0, "max": 100},
            "budget_level": {"type": "enum", "map": {"ok": 0.0, "warn": 0.5, "exceeded": 1.0}}
        },
        "mapping": [
            {"range": [0.00, 0.30], "action": {"mode": "promote", "step_inc": 10, "cap": 100}},
            {"range": [0.30, 0.55], "action": {"mode": "canary", "step_inc": 5, "cap": 50}},
            {"range": [0.55, 0.75], "action": {"mode": "canary", "step_inc": 2, "cap": 20}},
            {"range": [0.75, 1.00], "action": {"mode": "freeze", "step_inc": 0, "cap": 0}},
            {"range": [1.00, 9.99], "action": {"mode": "abort"}}
        ]
    }

    signals = {
        "drift_z": 0.0,  # 정상
        "anomaly_score": 0.0,  # 정상
        "infra_p95_ms": 300,  # 최소값 (정상)
        "error_rate": 0.0,  # 정상
        "quota_denies": 0,  # 정상
        "budget_level": "ok"  # 정상
    }

    gov = RiskGovernor(GovernorConfig(**config))
    risk_score, action = gov.decide(signals)

    assert risk_score < 0.3
    assert action["mode"] == "promote"
    assert action["step_inc"] == 10


@pytest.mark.gate_u
def test_medium_risk_canary():
    """중간 위험 → 0.3<risk<0.75 → canary 감속"""
    config = {
        "weights": {
            "drift_z": 0.35,
            "anomaly_score": 0.20,
            "infra_p95_ms": 0.15,
            "error_rate": 0.15,
            "quota_denies": 0.10,
            "budget_level": 0.05
        },
        "norm": {
            "drift_z": {"type": "zscore", "cap": 5.0},
            "anomaly_score": {"type": "linear", "min": 0, "max": 1},
            "infra_p95_ms": {"type": "minmax", "min": 300, "max": 2000},
            "error_rate": {"type": "minmax", "min": 0.0, "max": 0.05},
            "quota_denies": {"type": "minmax", "min": 0, "max": 100},
            "budget_level": {"type": "enum", "map": {"ok": 0.0, "warn": 0.5, "exceeded": 1.0}}
        },
        "mapping": [
            {"range": [0.00, 0.30], "action": {"mode": "promote", "step_inc": 10, "cap": 100}},
            {"range": [0.30, 0.55], "action": {"mode": "canary", "step_inc": 5, "cap": 50}},
            {"range": [0.55, 0.75], "action": {"mode": "canary", "step_inc": 2, "cap": 20}},
            {"range": [0.75, 1.00], "action": {"mode": "freeze", "step_inc": 0, "cap": 0}},
            {"range": [1.00, 9.99], "action": {"mode": "abort"}}
        ]
    }

    signals = {
        "drift_z": 2.0,  # 중간
        "anomaly_score": 0.3,  # 중간
        "infra_p95_ms": 800,  # 중간
        "error_rate": 0.02,  # 중간
        "quota_denies": 20,  # 중간
        "budget_level": "ok"
    }

    gov = RiskGovernor(GovernorConfig(**config))
    risk_score, action = gov.decide(signals)

    assert 0.3 <= risk_score < 0.75
    assert action["mode"] == "canary"
    assert action["step_inc"] in [5, 2]


@pytest.mark.gate_u
def test_high_risk_freeze():
    """높은 위험 → 0.75<risk<1.0 → freeze"""
    config = {
        "weights": {
            "drift_z": 0.35,
            "anomaly_score": 0.20,
            "infra_p95_ms": 0.15,
            "error_rate": 0.15,
            "quota_denies": 0.10,
            "budget_level": 0.05
        },
        "norm": {
            "drift_z": {"type": "zscore", "cap": 5.0},
            "anomaly_score": {"type": "linear", "min": 0, "max": 1},
            "infra_p95_ms": {"type": "minmax", "min": 300, "max": 2000},
            "error_rate": {"type": "minmax", "min": 0.0, "max": 0.05},
            "quota_denies": {"type": "minmax", "min": 0, "max": 100},
            "budget_level": {"type": "enum", "map": {"ok": 0.0, "warn": 0.5, "exceeded": 1.0}}
        },
        "mapping": [
            {"range": [0.00, 0.30], "action": {"mode": "promote", "step_inc": 10, "cap": 100}},
            {"range": [0.30, 0.55], "action": {"mode": "canary", "step_inc": 5, "cap": 50}},
            {"range": [0.55, 0.75], "action": {"mode": "canary", "step_inc": 2, "cap": 20}},
            {"range": [0.75, 1.00], "action": {"mode": "freeze", "step_inc": 0, "cap": 0}},
            {"range": [1.00, 9.99], "action": {"mode": "abort"}}
        ]
    }

    signals = {
        "drift_z": 4.0,  # 높음
        "anomaly_score": 0.8,  # 높음
        "infra_p95_ms": 1800,  # 높음
        "error_rate": 0.04,  # 높음
        "quota_denies": 80,  # 높음
        "budget_level": "warn"  # 경고
    }

    gov = RiskGovernor(GovernorConfig(**config))
    risk_score, action = gov.decide(signals)

    assert 0.75 <= risk_score < 1.0
    assert action["mode"] == "freeze"
    assert action["step_inc"] == 0


@pytest.mark.gate_u
def test_critical_risk_abort():
    """치명적 위험 → risk>1.0 → abort"""
    config = {
        "weights": {
            "drift_z": 0.35,
            "anomaly_score": 0.20,
            "infra_p95_ms": 0.15,
            "error_rate": 0.15,
            "quota_denies": 0.10,
            "budget_level": 0.05
        },
        "norm": {
            "drift_z": {"type": "zscore", "cap": 5.0},
            "anomaly_score": {"type": "linear", "min": 0, "max": 1},
            "infra_p95_ms": {"type": "minmax", "min": 300, "max": 2000},
            "error_rate": {"type": "minmax", "min": 0.0, "max": 0.05},
            "quota_denies": {"type": "minmax", "min": 0, "max": 100},
            "budget_level": {"type": "enum", "map": {"ok": 0.0, "warn": 0.5, "exceeded": 1.0}}
        },
        "mapping": [
            {"range": [0.00, 0.30], "action": {"mode": "promote", "step_inc": 10, "cap": 100}},
            {"range": [0.30, 0.55], "action": {"mode": "canary", "step_inc": 5, "cap": 50}},
            {"range": [0.55, 0.75], "action": {"mode": "canary", "step_inc": 2, "cap": 20}},
            {"range": [0.75, 1.00], "action": {"mode": "freeze", "step_inc": 0, "cap": 0}},
            {"range": [1.00, 9.99], "action": {"mode": "abort"}}
        ]
    }

    signals = {
        "drift_z": 5.0,  # 최대
        "anomaly_score": 1.0,  # 최대
        "infra_p95_ms": 2000,  # 최대
        "error_rate": 0.05,  # 최대
        "quota_denies": 100,  # 최대
        "budget_level": "exceeded"  # 초과
    }

    gov = RiskGovernor(GovernorConfig(**config))
    risk_score, action = gov.decide(signals)

    assert risk_score >= 1.0
    assert action["mode"] == "abort"
