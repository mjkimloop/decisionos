from __future__ import annotations

from collections import defaultdict
from typing import Dict


_COSTS: Dict[str, float] = defaultdict(float)


def add_cost(org_id: str, amount: float) -> None:
    try:
        _COSTS[org_id] += float(amount)
    except Exception:
        pass


def record_from_meta(org_id: str, route_meta: dict) -> None:
    amt = 0.0
    try:
        amt = float(route_meta.get("estimated_cost", 0.0))
    except Exception:
        amt = 0.0
    add_cost(org_id, amt)


def summary() -> dict:
    total = sum(_COSTS.values())
    return {"totals": dict(_COSTS), "total": round(total, 6)}

