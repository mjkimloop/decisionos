from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict

class MetricPlan(BaseModel):
    included: float = Field(ge=0.0, default=0.0)      # 포함량(무료)
    overage_rate: float = Field(ge=0.0, default=0.0)  # 초과 단가(통화 단위는 v1 생략)

class Plan(BaseModel):
    name: str
    metrics: Dict[str, MetricPlan]  # metric -> plan
