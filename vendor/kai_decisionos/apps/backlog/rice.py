from __future__ import annotations

from typing import Sequence


def compute_rice(reach: float, impact: float, confidence: float, effort: float) -> float:
    if effort <= 0:
        raise ValueError("effort must be >0")
    score = (reach * impact * confidence) / effort
    return round(score, 3)


def normalise_scores(scores: Sequence[float]) -> list[float]:
    total = sum(scores) or 1.0
    return [round(s / total, 4) for s in scores]


__all__ = ["compute_rice", "normalise_scores"]

