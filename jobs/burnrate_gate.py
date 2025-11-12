#!/usr/bin/env python3
"""
Burn-rate Gate Job
Error budget 소모율 게이트 (critical 시 비정상 종료)
"""
import os
import json
import sys
import argparse
from apps.sre.burnrate import load_burn_rate_config, compute_burn_rate, check_threshold
from apps.ops.metrics import update_burn_rate, increment_alert


def load_metrics(path: str = "var/metrics/errors.json") -> dict:
    """에러/요청 메트릭 로드"""
    if not os.path.exists(path):
        print(f"[WARN] Metrics file not found: {path}, using defaults")
        return {"errors": 0, "total": 1000}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_evidence_reason(reason: str, path: str = "var/evidence/gate_reasons.jsonl"):
    """Evidence에 reason 추가"""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    entry = {"reason": reason, "source": "burnrate_gate"}

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", default="var/metrics/errors.json")
    ap.add_argument("--config", default="configs/rollout/burn_rate.json")
    ap.add_argument("--evidence", default="var/evidence/gate_reasons.jsonl")
    args = ap.parse_args()

    # Load
    config = load_burn_rate_config(args.config)
    metrics = load_metrics(args.metrics)

    errors = metrics.get("errors", 0)
    total = metrics.get("total", 1000)

    # Compute burn rate
    burn_rate = compute_burn_rate(
        errors,
        total,
        config["objective"],
        config["window_sec"]
    )
    print(f"[INFO] Burn rate: {burn_rate:.4f}")

    # Check threshold
    level = check_threshold(burn_rate, config["thresholds"])
    print(f"[INFO] Threshold level: {level}")

    # Update metrics
    update_burn_rate(burn_rate)

    # Handle critical
    if level == "critical":
        print("[CRITICAL] Burn rate exceeded critical threshold!")
        write_evidence_reason("reason:budget-burn", args.evidence)
        increment_alert("critical")
        sys.exit(2)
    elif level == "warn":
        print("[WARN] Burn rate exceeded warn threshold")
        increment_alert("warn")
    else:
        print("[OK] Burn rate within acceptable range")

    sys.exit(0)


if __name__ == "__main__":
    main()
