from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, Tuple

class QuotaRule(BaseModel):
    soft: float = Field(ge=0.0)
    hard: float = Field(ge=0.0)

class QuotaConfig(BaseModel):
    # metric -> rule
    metrics: Dict[str, QuotaRule] = {}

class QuotaDecision(BaseModel):
    metric: str
    used: float
    soft: float
    hard: float
    action: str  # "allow" | "throttle" | "deny"

class InMemoryQuotaState:
    """v1 간단 상태 저장(tenant,metric → 누적 사용량)"""
    def __init__(self) -> None:
        self._acc: Dict[Tuple[str,str], float] = {}

    def add(self, tenant: str, metric: str, amount: float) -> float:
        key = (tenant, metric)
        cur = self._acc.get(key, 0.0) + float(amount)
        self._acc[key] = cur
        return cur

    def get(self, tenant: str, metric: str) -> float:
        return self._acc.get((tenant, metric), 0.0)

def decide_quota(used: float, rule: QuotaRule) -> str:
    if used > rule.hard:
        return "deny"
    if used > rule.soft:
        return "throttle"
    return "allow"

def apply_quota_batch(tenant: str, deltas: Dict[str, float], cfg: QuotaConfig, state: InMemoryQuotaState) -> list[QuotaDecision]:
    out: list[QuotaDecision] = []
    for metric, delta in deltas.items():
        rule = cfg.metrics.get(metric)
        if not rule:
            # 미정의 metric은 제한 없음
            out.append(QuotaDecision(metric=metric, used=state.add(tenant, metric, delta),
                                     soft=float("inf"), hard=float("inf"), action="allow"))
            continue
        used = state.add(tenant, metric, delta)
        action = decide_quota(used, rule)
        out.append(QuotaDecision(metric=metric, used=used, soft=rule.soft, hard=rule.hard, action=action))
    return out
