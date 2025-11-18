from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from apps.experiment.stage_file import write_stage_atomic

EVIDENCE_LATEST = Path(os.getenv("DECISIONOS_EVIDENCE_LATEST", "var/evidence/latest.json"))
REQUIRED_PASS = int(os.getenv("DECISIONOS_CANARY_REQUIRED_PASSES", "3"))
ALLOW_BURST = float(os.getenv("DECISIONOS_CANARY_MAX_BURST", "0"))
MIN_OBSERVATION_MIN = int(os.getenv("DECISIONOS_AUTOPROMOTE_MIN_OBSERVATION_MIN", "30"))


def _read_latest() -> Dict[str, Any]:
    return json.loads(EVIDENCE_LATEST.read_text(encoding="utf-8"))


def decide() -> str:
    evidence = _read_latest()
    canary = evidence.get("canary", {})
    windows: List[Dict[str, Any]] = canary.get("windows", [])
    if len(windows) < REQUIRED_PASS:
        return "hold"

    recent = windows[-REQUIRED_PASS:]
    if any(float(w.get("burst", 0)) > ALLOW_BURST for w in recent):
        return "abort"

    first_ts = float(recent[0].get("timestamp_unix", 0))
    last_ts = float(recent[-1].get("timestamp_unix", 0))
    if first_ts > 0 and last_ts > 0:
        observation_minutes = (last_ts - first_ts) / 60.0
        if observation_minutes < MIN_OBSERVATION_MIN:
            return "hold"

    if all(bool(w.get("pass", False)) for w in recent):
        return "promote"
    return "hold"


def main() -> None:
    if os.getenv("DECISIONOS_AUTOPROMOTE_ENABLE", "0") != "1":
        print("[auto-promote] disabled")
        raise SystemExit(0)
    if not EVIDENCE_LATEST.exists():
        print(f"[auto-promote] evidence missing: {EVIDENCE_LATEST}", file=sys.stderr)
        raise SystemExit(3)

    decision = decide()
    stage_path = os.getenv("STAGE_PATH")
    if decision == "promote":
        write_stage_atomic("promote", stage_path)
        print("[auto-promote] promote requested")
        raise SystemExit(0)
    if decision == "abort":
        write_stage_atomic("abort", stage_path)
        snapshot = _read_latest().get("canary", {}).get("windows", [])
        recent = snapshot[-REQUIRED_PASS:]
        burst_log = Path(os.getenv("DECISIONOS_CANARY_BURST_LOG", "var/evidence/canary-burst.json"))
        burst_log.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "decision": "abort",
            "cause": "burst_threshold",
            "max_burst": ALLOW_BURST,
            "required_pass": REQUIRED_PASS,
            "recent_window_count": len(recent),
            "observation_minutes": None,
            "windows": recent,
        }
        try:
            first_ts = float(recent[0].get("timestamp_unix", 0)) if recent else 0
            last_ts = float(recent[-1].get("timestamp_unix", 0)) if recent else 0
            if first_ts > 0 and last_ts > 0:
                meta["observation_minutes"] = (last_ts - first_ts) / 60.0
        except Exception:
            meta["observation_minutes"] = None
        burst_log.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[auto-promote] abort triggered due to burst/SLO failure (snapshot -> {burst_log})")
        raise SystemExit(2)

    print("[auto-promote] hold (insufficient data)")
    raise SystemExit(3)


if __name__ == "__main__":
    main()
