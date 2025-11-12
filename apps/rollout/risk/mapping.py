from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

@dataclass
class RangeAction:
    low: float
    high: float
    action: Dict[str, Any]

def normalize_mapping(rows: List[Dict[str, Any]]) -> List[RangeAction]:
    out: List[RangeAction] = []
    for r in rows:
        lo, hi = r.get("range", [0.0, 1.0])
        out.append(RangeAction(float(lo), float(hi), dict(r.get("action", {}))))
    return out

def map_score(mapping: List[RangeAction], score: float) -> Dict[str, Any]:
    for row in mapping:
        if row.low <= score < row.high:
            return row.action
    # fallback: most severe
    if mapping:
        return mapping[-1].action
    return {"mode": "freeze", "step_inc": 0, "cap": 0}

def decide(mapping_rows: List[Dict[str, Any]], score: float) -> Dict[str, Any]:
    return map_score(normalize_mapping(mapping_rows), score)
