import json
import os
import pytest
from jobs import risk_decide_and_stage as risk_job
from jobs import burnrate_gate as burn_job
from jobs import shadow_autotune as shadow_job

pytestmark = pytest.mark.gate_q

def test_risk_and_burn_jobs_with_tmp_env(tmp_path, monkeypatch):
    # 준비: config & inputs
    cfg_risk = tmp_path / "risk.json"
    signals = tmp_path / "signals.json"
    stage_dir = tmp_path / "stage"
    cfg_burn = tmp_path / "burn.json"
    perf = tmp_path / "perf.json"

    cfg_risk.write_text(json.dumps({
        "weights":{"drift_z":0.35,"anomaly_score":0.2,"infra_p95_ms":0.15,"error_rate":0.15,"quota_denies":0.1,"budget_level":0.05},
        "norm":{
            "drift_z":{"type":"zscore","cap":5.0},
            "anomaly_score":{"type":"linear","min":0,"max":1},
            "infra_p95_ms":{"type":"minmax","min":300,"max":2000},
            "error_rate":{"type":"minmax","min":0.0,"max":0.05},
            "quota_denies":{"type":"minmax","min":0,"max":100},
            "budget_level":{"type":"enum","map":{"ok":0.0,"warn":0.5,"exceeded":1.0}}
        },
        "mapping":[
            {"range":[0.0,0.3], "action":{"mode":"promote","step_inc":10,"cap":100}},
            {"range":[0.3,0.55], "action":{"mode":"canary","step_inc":5,"cap":50}},
            {"range":[0.55,0.75], "action":{"mode":"canary","step_inc":2,"cap":20}},
            {"range":[0.75,1.0], "action":{"mode":"freeze","step_inc":0,"cap":0}},
            {"range":[1.0,9.99], "action":{"mode":"abort"}}
        ]
    }), encoding="utf-8")
    signals.write_text(json.dumps({"drift_z":0.2,"anomaly_score":0.1,"infra_p95_ms":600,"error_rate":0.002,"quota_denies":0,"budget_level":"ok"}), encoding="utf-8")
    cfg_burn.write_text(json.dumps({"objective":{"target_availability":0.995},"window_sec":3600,"thresholds":{"warn":1.0,"critical":2.0}}), encoding="utf-8")
    perf.write_text(json.dumps({"total":10000,"errors":8}), encoding="utf-8")

    # env patch BEFORE importing modules (reload needed for global vars to update)
    monkeypatch.setenv("DECISIONOS_RISK_CFG", str(cfg_risk))
    monkeypatch.setenv("DECISIONOS_SIGNALS", str(signals))
    monkeypatch.setenv("DECISIONOS_STAGE_DIR", str(stage_dir))
    monkeypatch.setenv("DECISIONOS_BURN_CFG", str(cfg_burn))
    monkeypatch.setenv("DECISIONOS_BURN_INPUT", str(perf))

    # Reload modules to pick up env vars
    import importlib
    importlib.reload(risk_job)
    importlib.reload(burn_job)

    # burn gate
    assert burn_job.main([]) == 0

    # risk decide (stage 파일 생성)
    assert risk_job.main([]) == 0
    desired = stage_dir / "desired_stage.txt"
    meta = stage_dir / "desired_meta.json"
    assert desired.exists() and meta.exists()
    assert desired.read_text(encoding="utf-8").strip() in {"promote","canary","freeze","abort"}

def test_shadow_autotune_writes_percent(tmp_path, monkeypatch):
    cfg = tmp_path / "sampler.json"
    sig = tmp_path / "signals.json"
    out = tmp_path / "shadow" / "pct.txt"

    cfg.write_text(json.dumps({"min_pct":1,"max_pct":10,"hysteresis":{"up_ms":0,"down_ms":0}}), encoding="utf-8")
    sig.write_text(json.dumps({"cpu":0.2,"queue_depth":0}), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_SHADOW_CFG", str(cfg))
    monkeypatch.setenv("DECISIONOS_SHADOW_SIGNALS", str(sig))
    monkeypatch.setenv("DECISIONOS_SHADOW_OUT", str(out))

    # Reload module to pick up env vars
    import importlib
    importlib.reload(shadow_job)

    assert shadow_job.main([]) == 0
    assert out.exists()
    pct = int(out.read_text(encoding="utf-8").strip())
    assert 1 <= pct <= 10
