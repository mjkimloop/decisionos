from __future__ import annotations
import json, os
from datetime import datetime, timezone
from typing import Any, Dict
from apps.experiment.shadow_sampler import ShadowSampler, SamplerConfig, Hysteresis
from apps.ops.metrics import set_shadow_pct

CFG = os.environ.get("DECISIONOS_SHADOW_CFG", "configs/shadow/sampler.json")
SIGNALS = os.environ.get("DECISIONOS_SHADOW_SIGNALS", "var/evidence/shadow_signals.json")
OUT = os.environ.get("DECISIONOS_SHADOW_OUT", "var/shadow/sampler_pct.txt")

def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(argv: list[str] | None = None) -> int:
    if not os.path.exists(CFG):
        print(f"[WARN] Shadow config not found: {CFG}, using defaults")
        cfg_dict = {"min_pct": 1, "max_pct": 50, "hysteresis": {"up_ms": 900, "down_ms": 300}}
    else:
        cfg_dict = _load_json(CFG)
    hysteresis = cfg_dict.get("hysteresis", {})
    sampler = ShadowSampler(SamplerConfig(
        min_pct=int(cfg_dict.get("min_pct", 1)),
        max_pct=int(cfg_dict.get("max_pct", 50)),
        hysteresis=Hysteresis(up_ms=int(hysteresis.get("up_ms", 900)),
                              down_ms=int(hysteresis.get("down_ms", 300)))
    ))
    signals = _load_json(SIGNALS) if os.path.exists(SIGNALS) else {"cpu": 0.3, "queue_depth": 10}
    pct = sampler.update(signals)
    set_shadow_pct(pct)
    os.makedirs(os.path.dirname(OUT) if os.path.dirname(OUT) else ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(str(pct))
    print(f"[shadow_autotune] pct={pct}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
