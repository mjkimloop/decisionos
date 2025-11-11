from __future__ import annotations
import os, json, sys
from typing import Any, Dict, List
from apps.experiment.stage_file import write_stage_atomic

EVIDENCE_LATEST = os.getenv("DECISIONOS_EVIDENCE_LATEST", "var/evidence/latest.json")
REQUIRED_PASS = int(os.getenv("DECISIONOS_AUTO_PROMOTE_N", "3"))
ALLOW_BURST = int(os.getenv("DECISIONOS_AUTO_PROMOTE_MAX_BURST", "0"))

def _read_latest() -> Dict[str, Any]:
    with open(EVIDENCE_LATEST, "r", encoding="utf-8") as f:
        return json.load(f)

def decide() -> str:
    ev = _read_latest()
    canary = ev.get("canary", {})
    windows: List[Dict[str, Any]] = canary.get("windows", [])
    if len(windows) < REQUIRED_PASS:
        return "hold"

    recent = windows[-REQUIRED_PASS:]
    if any(w.get("burst", 0) > ALLOW_BURST for w in recent):
        return "abort"
    if all(w.get("pass", False) for w in recent):
        return "promote"
    return "hold"

def main():
    decision = decide()
    stage_path = os.getenv("STAGE_PATH")
    if decision == "promote":
        write_stage_atomic("promote", stage_path)
        print("[auto-promote] stage=promote")
        sys.exit(0)
    elif decision == "abort":
        write_stage_atomic("abort", stage_path)
        print("[auto-abort] stage=abort")
        sys.exit(2)
    else:
        print("[auto-hold] no action")
        sys.exit(3)

if __name__ == "__main__":
    main()
