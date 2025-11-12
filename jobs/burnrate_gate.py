from __future__ import annotations
import argparse, json, os, sys
from typing import Any, Dict
from apps.sre.burnrate import BurnRateConfig, compute_burn_rate, evaluate_burn_rate
from apps.ops.metrics import observe_burn_rate

def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.environ.get("DECISIONOS_BURN_CFG", "configs/rollout/burn_rate.json"))
    ap.add_argument("--metrics", default=os.environ.get("DECISIONOS_BURN_INPUT", "var/evidence/perf.json"))
    ap.add_argument("--evidence", default="var/evidence/gate_reasons.jsonl")
    args = ap.parse_args(argv)

    cfg = _load_json(args.config)
    perf = _load_json(args.metrics) if os.path.exists(args.metrics) else {"total": 0, "errors": 0}
    br_cfg = BurnRateConfig(
        target_availability=cfg.get("objective",{}).get("target_availability", 0.995),
        window_sec=int(cfg.get("window_sec", 3600)),
        thresholds=cfg.get("thresholds", {"warn":1.0,"critical":2.0})
    )
    br = compute_burn_rate(int(perf.get("total",0)), int(perf.get("errors",0)), br_cfg)
    lvl = evaluate_burn_rate(br, br_cfg)
    observe_burn_rate(br)

    msg = f"[burn_gate] burn_rate={br:.3f} level={lvl}"
    if lvl == "ok":
        print(msg)
        print("[OK] Burn rate gate passed")
    elif lvl == "warn":
        print(msg)
        print("[WARN] Burn rate elevated but within acceptable range")
    else:
        print(msg)
        print("[CRITICAL] Burn rate exceeded threshold - blocking deployment")
        # Write evidence for critical burn rate
        os.makedirs(os.path.dirname(args.evidence) if os.path.dirname(args.evidence) else ".", exist_ok=True)
        with open(args.evidence, "a", encoding="utf-8") as f:
            evidence = {
                "level": "critical",
                "reason": "reason:budget-burn",
                "burn_rate": br,
                "threshold": br_cfg.thresholds.get("critical", 2.0) if br_cfg.thresholds else 2.0,
                "message": f"Error budget burn rate {br:.2f}x exceeds critical threshold"
            }
            f.write(json.dumps(evidence, ensure_ascii=False) + "\n")

    if lvl == "critical":
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
