from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple
from .mapping import decide as mapping_decide

@dataclass
class GovernorConfig:
    weights: Dict[str, float]
    norm: Dict[str, Dict[str, Any]]
    mapping: list

def _minmax(x: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    v = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, v))

def _enum(v: Any, table: Dict[str, float]) -> float:
    return float(table.get(str(v), 0.0))

def _norm_one(key: str, x: float, spec: Dict[str, Any]) -> float:
    t = spec.get("type", "minmax")
    if t == "minmax":
        return _minmax(x, float(spec.get("min", 0.0)), float(spec.get("max", 1.0)))
    if t == "linear":
        return _minmax(x, float(spec.get("min", 0.0)), float(spec.get("max", 1.0)))
    if t == "zscore":
        # z-score는 입력이 이미 z라 가정하고 0~cap로 클립 후 cap로 나눠 정규화
        cap = float(spec.get("cap", 5.0))
        return _minmax(abs(x), 0.0, cap)
    if t == "enum":
        return _enum(x, dict(spec.get("map", {})))
    # unknown → 0
    return 0.0

class RiskGovernor:
    def __init__(self, cfg: GovernorConfig):
        self.cfg = cfg

    def score(self, signals: Dict[str, Any]) -> float:
        wsum = 0.0
        wtot = 0.0
        for k, w in self.cfg.weights.items():
            wtot += float(w)
            v = signals.get(k, 0.0)
            spec = self.cfg.norm.get(k, {"type": "minmax", "min": 0.0, "max": 1.0})
            # Don't convert to float for enum types
            if spec.get("type") == "enum":
                n = _norm_one(k, v, spec)
            else:
                n = _norm_one(k, float(v) if not isinstance(v, str) else 0.0, spec)
            wsum += float(w) * n
        if wtot <= 0:
            return 0.0
        s = wsum / wtot
        # 안전 클램프
        return max(0.0, min(9.99, s))

    def decide(self, signals: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        s = self.score(signals)
        action = mapping_decide(self.cfg.mapping, s)
        return s, action
