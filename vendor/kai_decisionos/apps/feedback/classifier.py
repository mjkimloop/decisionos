from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence


def classify_feedback(rating: int) -> str:
    if rating >= 9:
        return "promoter"
    if rating >= 7:
        return "passive"
    return "detractor"


def aggregate_feedback(ratings: Sequence[int]) -> dict[str, float]:
    counts = Counter(classify_feedback(r) for r in ratings)
    total = sum(counts.values()) or 1
    promoter = counts.get("promoter", 0)
    detractor = counts.get("detractor", 0)
    nps = ((promoter - detractor) / total) * 100
    return {
        "counts": dict(counts),
        "nps": round(nps, 2),
    }


__all__ = ["classify_feedback", "aggregate_feedback"]

