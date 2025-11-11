from __future__ import annotations
import random, math
from typing import Dict, Any, List

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

def _percentile(v: List[float], p: float) -> float:
    if not v: return float("nan")
    v2 = sorted(v)
    k = max(0, min(len(v2)-1, int(math.ceil(p * len(v2)))-1))
    return v2[k]

def simulate_ab_bootstrap(history: Dict[str, Dict[str, List[float]]],
                          baseline_weights: Dict[str, float],
                          candidate_weights: Dict[str, float],
                          traffic_split: float = 0.5,
                          iters: int = 500,
                          seed: int = 42) -> Dict[str, Any]:
    """
    history: {"infra":{"incidents":[...], "cost":[...]}, "perf":{...}}
    단순 부트스트랩(유니폼 리샘플). 외부 의존 없이 빠르게 동작.
    """
    rng = random.Random(seed)

    def sample_stats() -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for g, s in history.items():
            incs = s.get("incidents", [0.0])
            costs = s.get("cost", [0.0])
            inc = incs[rng.randrange(len(incs))] if incs else 0.0
            cst = costs[rng.randrange(len(costs))] if costs else 0.0
            out[g] = {"incidents": float(inc), "cost": float(cst)}
        return out

    base_samples, cand_samples, delta_samples = [], [], []
    for _ in range(iters):
        stats = sample_stats()
        b = _weighted_objective(stats, baseline_weights)
        c = _weighted_objective(stats, candidate_weights)
        base_samples.append(b); cand_samples.append(c); delta_samples.append(c - b)

    def summarize(v: List[float]) -> Dict[str, float]:
        if not v: return {"mean": float("nan"), "var": float("nan"), "ci95_low": float("nan"), "ci95_high": float("nan")}
        mean = sum(v) / len(v)
        var = sum((x - mean) ** 2 for x in v) / (len(v) - 1) if len(v) > 1 else 0.0
        return {"mean": mean, "var": var, "ci95_low": _percentile(v, 0.025), "ci95_high": _percentile(v, 0.975)}

    base_s = summarize(base_samples)
    cand_s = summarize(cand_samples)
    delta_s = summarize(delta_samples)
    p_win = sum(1 for d in delta_samples if d > 0) / max(1, len(delta_samples))

    risk = abs(delta_s["mean"]) * (1.0 - min(max(traffic_split, 0.0), 1.0))

    return {
        "baseline": base_s,
        "candidate": cand_s,
        "delta": {**delta_s, "p_win": p_win, "risk": risk},
        "bootstrap": {"iters": iters, "seed": seed}
    }
