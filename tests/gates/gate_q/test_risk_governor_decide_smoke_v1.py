import pytest
from apps.rollout.risk.governor import GovernorConfig, RiskGovernor

pytestmark = pytest.mark.gate_q

def test_risk_governor_decide_basic():
    cfg = GovernorConfig(
        weights={"drift_z":0.35,"anomaly_score":0.2,"infra_p95_ms":0.15,"error_rate":0.15,"quota_denies":0.1,"budget_level":0.05},
        norm={
            "drift_z":{"type":"zscore","cap":5.0},
            "anomaly_score":{"type":"linear","min":0,"max":1},
            "infra_p95_ms":{"type":"minmax","min":300,"max":2000},
            "error_rate":{"type":"minmax","min":0.0,"max":0.05},
            "quota_denies":{"type":"minmax","min":0,"max":100},
            "budget_level":{"type":"enum","map":{"ok":0.0,"warn":0.5,"exceeded":1.0}}
        },
        mapping=[
            {"range":[0.00,0.30], "action":{"mode":"promote","step_inc":10,"cap":100}},
            {"range":[0.30,0.55], "action":{"mode":"canary","step_inc":5,"cap":50}},
            {"range":[0.55,0.75], "action":{"mode":"canary","step_inc":2,"cap":20}},
            {"range":[0.75,1.00], "action":{"mode":"freeze","step_inc":0,"cap":0}},
            {"range":[1.00,9.99], "action":{"mode":"abort"}}
        ],
    )
    signals = {"drift_z":0.2,"anomaly_score":0.1,"infra_p95_ms":600,"error_rate":0.002,"quota_denies":0,"budget_level":"ok"}
    gov = RiskGovernor(cfg)
    score, action = gov.decide(signals)
    assert 0.0 <= score <= 9.99
    assert action["mode"] in {"promote","canary","freeze","abort"}
