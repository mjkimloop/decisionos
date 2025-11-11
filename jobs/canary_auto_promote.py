from __future__ import annotations
import os, json, sys
from typing import Any, Dict, List
from apps.experiment.stage_file import write_stage_atomic
from pathlib import Path

EVIDENCE_LATEST = os.getenv("DECISIONOS_EVIDENCE_LATEST", "var/evidence/latest.json")
REQUIRED_PASS = int(os.getenv("DECISIONOS_AUTO_PROMOTE_N", "5"))
ALLOW_BURST = int(os.getenv("DECISIONOS_AUTO_PROMOTE_MAX_BURST", "1"))
MIN_OBSERVATION_MIN = int(os.getenv("DECISIONOS_AUTO_PROMOTE_MIN_OBSERVATION_MIN", "30"))

def _load_policy(path: str) -> Dict[str, Any]:
    """카나리 정책 v2 로드 (defaults 포함)"""
    with open(path, "r", encoding="utf-8") as f:
        p = json.load(f)
    # v2 defaults
    p.setdefault("holdback_pct_min", 0)
    p.setdefault("cooldown_sec", 300)
    p.setdefault("stickiness", "none")
    p.setdefault("ewma_tolerance", 0.3)
    p.setdefault("burst_threshold", 0.5)
    p.setdefault("step_schedule", [])
    return p

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

    # 버스트 체크: 최근 N개 윈도우 중 ALLOW_BURST 초과 시 abort
    if any(w.get("burst", 0) > ALLOW_BURST for w in recent):
        return "abort"

    # 최소 관찰 시간 체크 (분 단위)
    first_timestamp = recent[0].get("timestamp_unix", 0)
    last_timestamp = recent[-1].get("timestamp_unix", 0)
    observation_minutes = (last_timestamp - first_timestamp) / 60.0
    if observation_minutes < MIN_OBSERVATION_MIN:
        return "hold"

    # 모든 윈도우 통과 시 promote
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
