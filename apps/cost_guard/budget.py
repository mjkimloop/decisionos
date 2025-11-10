from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

class BudgetPolicy(BaseModel):
    monthly_limit: float = Field(ge=0.0)
    warn_ratio: float = Field(ge=0.0, le=1.0, default=0.8)  # 80% 경보

class BudgetEvent(BaseModel):
    level: Literal["ok","warn","limit","exceeded"]
    spent: float
    limit: float

def check_budget(spent: float, policy: BudgetPolicy) -> BudgetEvent:
    if spent >= policy.monthly_limit:
        return BudgetEvent(level="exceeded", spent=round(spent,6), limit=policy.monthly_limit)
    if spent >= policy.monthly_limit * policy.warn_ratio:
        return BudgetEvent(level="warn", spent=round(spent,6), limit=policy.monthly_limit)
    return BudgetEvent(level="ok", spent=round(spent,6), limit=policy.monthly_limit)
