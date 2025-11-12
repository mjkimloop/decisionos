from __future__ import annotations
import json, os, sys
from typing import Any, Dict, Tuple
from apps.rollout.risk.governor import GovernorConfig, RiskGovernor
from apps.ops.metrics import observe_risk_score

CFG_RISK = os.environ.get("DECISIONOS_RISK_CFG", "configs/rollout/risk_governor.json")
SIGNALS_JSON = os.environ.get("DECISIONOS_SIGNALS", "var/evidence/signals.json")
STAGE_DIR = os.environ.get("DECISIONOS_STAGE_DIR", "var/rollout")

def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dirs() -> None:
    os.makedirs(STAGE_DIR, exist_ok=True)

def write_stage(mode: str, meta: Dict[str, Any]) -> None:
    ensure_dirs()
    with open(os.path.join(STAGE_DIR, "desired_stage.txt"), "w", encoding="utf-8") as f:
        f.write(mode)
    with open(os.path.join(STAGE_DIR, "desired_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def main(argv: list[str] | None = None) -> int:
    cfg = _load_json(CFG_RISK)
    signals = _load_json(SIGNALS_JSON) if os.path.exists(SIGNALS_JSON) else {}
    gov = RiskGovernor(GovernorConfig(**cfg))
    score, action = gov.decide(signals)
    observe_risk_score(score)
    mode = action.get("mode", "freeze")
    meta = {"score": score, "action": action, "signals": signals}
    write_stage(mode, meta)
    print(f"[risk_decide] score={score:.3f} action={action}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
