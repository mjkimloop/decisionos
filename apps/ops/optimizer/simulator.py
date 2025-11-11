from __future__ import annotations
from typing import Dict, Any

def _weighted_objective(index_stats: Dict[str, Dict[str, float]], weights: Dict[str, float]) -> float:
    # index_stats 예: {"infra":{"incidents":12,"cost":3.2}, ...}
    score, penalty = 0.0, 0.0
    for g, s in index_stats.items():
        w = float(weights.get(g, 1.0))
        incidents = float(s.get("incidents", 0.0))
        cost = float(s.get("cost", 0.0))
        score += w * max(0.0, 10.0 - incidents)
        penalty += (incidents * 0.5 + cost) * (w ** 0.5)
    return score - penalty

def simulate_ab(index_stats: Dict[str, Dict[str, float]],
                baseline_weights: Dict[str, float],
                candidate_weights: Dict[str, float],
                traffic_split: float = 0.5) -> Dict[str, Any]:
    """
    단순 기대효과 비교. traffic_split은 리스크 보정 가중에 사용.
    """
    base = _weighted_objective(index_stats, baseline_weights)
    cand = _weighted_objective(index_stats, candidate_weights)
    delta = cand - base
    risk = abs(delta) * (1.0 - min(max(traffic_split, 0.0), 1.0))  # 카나리 트래픽이 적을수록 리스크 낮게
    return {
        "baseline": {"objective": base},
        "candidate": {"objective": cand},
        "delta": {"objective": delta, "risk": risk}
    }
