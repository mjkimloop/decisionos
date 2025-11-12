#!/usr/bin/env python3
"""
Risk Decide and Stage Job
risk_score 계산 및 desired_stage 결정
"""
import os
import json
import argparse
from apps.rollout.risk.governor import load_governor_config, compute_risk_score, get_action
from apps.ops.metrics import update_risk_score


def load_signals(path: str = "var/signals/current.json") -> dict:
    """신호 데이터 로드"""
    if not os.path.exists(path):
        print(f"[WARN] Signals file not found: {path}, using defaults")
        return {
            "drift_z": 0.0,
            "anomaly_score": 0.0,
            "infra_p95_ms": 300,
            "error_rate": 0.0,
            "quota_denies": 0,
            "budget_level": "ok"
        }

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", default="var/signals/current.json")
    ap.add_argument("--config", default="configs/rollout/risk_governor.json")
    ap.add_argument("--stage-out", default="var/rollout/desired_stage.txt")
    ap.add_argument("--meta-out", default="var/rollout/desired_meta.json")
    args = ap.parse_args()

    # Load
    signals = load_signals(args.signals)
    config = load_governor_config(args.config)

    # Compute risk score
    risk_score = compute_risk_score(signals, config)
    print(f"[INFO] Risk score: {risk_score:.4f}")

    # Get action
    action = get_action(risk_score, config["mapping"])
    print(f"[INFO] Action: {action}")

    # Write stage file
    os.makedirs(os.path.dirname(args.stage_out) if os.path.dirname(args.stage_out) else ".", exist_ok=True)
    with open(args.stage_out, "w", encoding="utf-8") as f:
        f.write(action.get("mode", "freeze"))

    # Write meta file
    os.makedirs(os.path.dirname(args.meta_out) if os.path.dirname(args.meta_out) else ".", exist_ok=True)
    meta = {
        "risk_score": risk_score,
        "action": action,
        "signals": signals
    }
    with open(args.meta_out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Update metrics
    update_risk_score(risk_score)

    print(f"[OK] Stage decision written to {args.stage_out}")
    print(f"[OK] Meta written to {args.meta_out}")


if __name__ == "__main__":
    main()
