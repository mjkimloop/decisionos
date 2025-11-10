from __future__ import annotations

from typing import List, Dict, Any


def null_rate(records: List[Dict[str, Any]], key: str) -> float:
    total = len(records)
    if total == 0:
        return 0.0
    nulls = sum(1 for r in records if r.get(key) in (None, ""))
    return round(nulls / total, 4)


def distinct_ratio(records: List[Dict[str, Any]], key: str) -> float:
    total = len(records)
    if total == 0:
        return 0.0
    values = {r.get(key) for r in records if key in r}
    return round(len(values) / total, 4)


def compute_quality(records: List[Dict[str, Any]], keys: List[str]) -> Dict[str, Dict[str, float]]:
    return {
        key: {
            "null_rate": null_rate(records, key),
            "distinct_ratio": distinct_ratio(records, key),
        }
        for key in keys
    }


__all__ = ["compute_quality", "null_rate", "distinct_ratio"]
