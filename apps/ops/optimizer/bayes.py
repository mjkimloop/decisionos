# Minimal, dependency-optional Bayesian-like optimizer
from __future__ import annotations
import json, math, random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class HistoryPoint:
    # 예: 기간별 운영 결과(라벨 카운트, 비용, 실패율 등)로부터 산출한 목적함수 값
    weights: Dict[str, float]  # group -> weight
    objective: float           # 높을수록 좋음(또는 낮을수록 → sign 반전)
    meta: Dict[str, float]     # 참고용 지표

@dataclass
class SearchSpace:
    bounds: Dict[str, Tuple[float, float]]  # group -> (min, max)

class WeightOptimizer:
    def __init__(self, space: SearchSpace, seed: int = 42):
        self.space = space
        random.seed(seed)

    def _sample_weights(self) -> Dict[str, float]:
        return {g: random.uniform(lo, hi) for g, (lo,hi) in self.space.bounds.items()}

    def _score(self, weights: Dict[str, float], loglik: callable) -> float:
        # loglik: evidence index/label-trend로부터 정의되는 로그우도 추정(또는 유사 목적함수)
        return loglik(weights)

    def suggest(self, history: List[HistoryPoint], loglik: callable, n_iter: int = 40) -> Dict[str, float]:
        # 의존성 없이 동작하는 간이 베이지안 탐색(랜덤 탐색 + 탐욕적 개선)
        # skopt가 있으면 대체 가능
        best_w, best_s = None, -1e9
        # 초기 후보: 히스토리 최선
        for hp in history:
            if hp.objective > best_s:
                best_s, best_w = hp.objective, hp.weights
        # 랜덤 탐색
        for _ in range(n_iter):
            w = self._sample_weights()
            s = self._score(w, loglik)
            if s > best_s:
                best_s, best_w = s, w
        # 국소 탐색(작은 노이즈)
        for _ in range(20):
            w = {g: max(self.space.bounds[g][0], min(self.space.bounds[g][1], best_w[g] + random.uniform(-0.05, 0.05))) for g in best_w}
            s = self._score(w, loglik)
            if s > best_s:
                best_s, best_w = s, w
        return best_w or self._sample_weights()

def build_space_from_catalog(catalog_path: str) -> SearchSpace:
    with open(catalog_path, "r", encoding="utf-8") as f:
        cat = json.load(f)
    bounds = {}
    for g, meta in cat.get("groups", {}).items():
        w = float(meta.get("weight", 1.0))
        # 기본 범위: ±50% (운영에서 조정)
        bounds[g] = (max(0.1, w * 0.5), w * 1.5)
    return SearchSpace(bounds=bounds)

def default_loglik_from_index(index_stats: Dict[str, Dict[str, float]]):
    # 간단한 목적: (가중 점수 대비 실패/에러 비용 최소화) → 점수 높을수록 좋음
    # index_stats 예: {"infra": {"incidents": 12, "cost": 3.2}, "perf": {...}}
    def _f(weights: Dict[str, float]) -> float:
        score = 0.0
        penalty = 0.0
        for g, w in weights.items():
            s = index_stats.get(g, {})
            incidents = float(s.get("incidents", 0.0))
            cost = float(s.get("cost", 0.0))
            score += w * max(0.0, 10.0 - incidents)   # 적을수록 우대
            penalty += (incidents * 0.5 + cost) * (w ** 0.5)
        return score - penalty
    return _f
