from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List

class EwmaConfig(BaseModel):
    alpha: float = Field(gt=0.0, lt=1.0, default=0.3)
    spike_ratio: float = Field(ge=0.0, default=0.5)  # 현재값 > ewma*(1+ratio) → 이상

class AnomalyResult(BaseModel):
    ewma: float
    is_spike: bool

def ewma_detect(series: List[float], cfg: EwmaConfig) -> AnomalyResult:
    if not series:
        return AnomalyResult(ewma=0.0, is_spike=False)
    ewma = series[0]
    for v in series[1:]:
        ewma = cfg.alpha * v + (1 - cfg.alpha) * ewma
    cur = series[-1]
    is_spike = cur > ewma * (1 + cfg.spike_ratio)
    return AnomalyResult(ewma=round(ewma,6), is_spike=is_spike)
