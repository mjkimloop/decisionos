from __future__ import annotations
import os, json
from typing import Dict

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "infra": 3.0,
    "perf": 2.0,
    "canary": 2.5,
    "quota": 1.5,
    "budget": 1.8,
    "anomaly": 1.7,
}

def group_of(label: str) -> str:
    # 예: reason:infra-latency → infra, reason:budget-exceeded → budget
    if not label.startswith("reason:"):
        return "other"
    body = label.split("reason:", 1)[1]
    if body == "budget-exceeded":
        return "budget"
    head = body.split("-", 1)[0]
    return head

def load_group_weights() -> Dict[str, float]:
    raw = os.environ.get("REASON_GROUP_WEIGHTS", "").strip()
    if not raw:
        return dict(_DEFAULT_WEIGHTS)
    try:
        obj = json.loads(raw)
        base = dict(_DEFAULT_WEIGHTS)
        base.update({str(k): float(v) for (k, v) in obj.items()})
        return base
    except Exception:
        return dict(_DEFAULT_WEIGHTS)
