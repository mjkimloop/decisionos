#!/usr/bin/env python3
"""
Canary Step Adjust Job
drift severity에 따른 canary step 자동 조정
- critical: canary 즉시 중단
- warn: step/max 감속
- info: 정상 진행
"""
import os
import json
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drift-path", default="var/alerts/posterior_drift.json")
    ap.add_argument("--canary-config", default="configs/canary/policy.autotuned.json")
    ap.add_argument("--out", default="configs/canary/policy.autotuned.json")
    args = ap.parse_args()

    # Load drift
    if not os.path.exists(args.drift_path):
        print(f"[INFO] No drift data at {args.drift_path}, skip canary adjust")
        return

    drift = json.load(open(args.drift_path, "r", encoding="utf-8"))
    severity = drift.get("severity", "info")

    # Load canary config
    canary = {"canary": {"enabled": True, "step_pct": 10, "max_pct": 50}}
    if os.path.exists(args.canary_config):
        canary = json.load(open(args.canary_config, "r", encoding="utf-8"))

    # Ensure canary block exists
    if "canary" not in canary:
        canary["canary"] = {"enabled": True, "step_pct": 10, "max_pct": 50}

    # Adjust based on severity
    if severity == "critical":
        # 즉시 중단
        canary["canary"]["enabled"] = False
        print(f"[CRITICAL] Canary disabled due to critical drift")
    elif severity == "warn":
        # 증분·상한 감속
        current_step = canary["canary"].get("step_pct", 10)
        current_max = canary["canary"].get("max_pct", 50)

        new_step = max(5, int(current_step * 0.5))
        new_max = max(30, int(current_max * 0.7))

        canary["canary"]["step_pct"] = new_step
        canary["canary"]["max_pct"] = new_max
        print(f"[WARN] Canary reduced: step_pct={new_step}, max_pct={new_max}")
    else:
        # 정상 진행 (info or unknown)
        canary["canary"]["enabled"] = True
        canary["canary"]["step_pct"] = 10
        canary["canary"]["max_pct"] = 50
        print(f"[INFO] Canary normal: step_pct=10, max_pct=50")

    # Write output
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(canary, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Canary config updated → {args.out}")


if __name__ == "__main__":
    main()
