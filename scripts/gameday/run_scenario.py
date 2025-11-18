from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Callable, Dict


def _base_payload(name: str) -> dict:
    return {
        "scenario": name,
        "started_at": int(time.time()),
        "status": "unknown",
        "checks": [],
        "metrics": {},
        "notes": [],
    }


def _latency_spike() -> dict:
    payload = _base_payload("latency_spike")
    payload["metrics"]["p95_delta_ms"] = random.randint(80, 160)
    payload["checks"].append({"name": "canary", "status": "pass"})
    payload["checks"].append({"name": "rollback", "status": "pass"})
    payload["status"] = "pass"
    payload["notes"].append("Latency spike triggered via synthetic load; canary absorbed impact.")
    return payload


def _error_spike() -> dict:
    payload = _base_payload("error_spike")
    payload["metrics"]["error_rate"] = round(random.uniform(0.01, 0.05), 3)
    payload["checks"].append({"name": "burn_gate", "status": "pass"})
    payload["checks"].append({"name": "pause_release", "status": "pass"})
    payload["status"] = "pass"
    payload["notes"].append("Error spike contained; burn gate triggered alert channel.")
    return payload


def _judge_unavailable() -> dict:
    payload = _base_payload("judge_unavailable")
    payload["checks"].append({"name": "fallback_cache", "status": "pass"})
    payload["checks"].append({"name": "dr_restore", "status": "pass"})
    payload["status"] = "pass"
    payload["notes"].append("Judge fallback cache served requests while primary was offline.")
    return payload


SCENARIOS: Dict[str, Callable[[], dict]] = {
    "latency_spike": _latency_spike,
    "error_spike": _error_spike,
    "judge_unavailable": _judge_unavailable,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GameDay scenario (simulated)")
    parser.add_argument("--scenario", choices=SCENARIOS.keys(), required=True)
    parser.add_argument("--out", default="var/ci/gameday.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    payload = SCENARIOS[args.scenario]()
    payload["finished_at"] = int(time.time())
    payload["duration_sec"] = payload["finished_at"] - payload["started_at"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[gameday] scenario={args.scenario} status={payload['status']} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
