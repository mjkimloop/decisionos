from __future__ import annotations

from fastapi import APIRouter, Header, Depends
from typing import Optional

from packages.schemas.api import DecisionRequest, DecisionResponse
from apps.executor.pipeline import decide as do_decide
from apps.executor.exceptions import DomainError


router = APIRouter()


def auth_dep():
    return None


@router.post("/api/v1/decide/{contract}", response_model=DecisionResponse)
def decide(contract: str, body: DecisionRequest,
           x_budget_latency: Optional[float] = Header(default=None, alias="X-Budget-Latency"),
           x_budget_cost: Optional[float] = Header(default=None, alias="X-Budget-Cost"),
           x_budget_accuracy: Optional[float] = Header(default=None, alias="X-Budget-Accuracy"),
           _: None = Depends(auth_dep)):
    budgets = {}
    if x_budget_latency is not None:
        budgets["latency"] = x_budget_latency
    if x_budget_cost is not None:
        budgets["cost"] = x_budget_cost
    if x_budget_accuracy is not None:
        budgets["accuracy"] = x_budget_accuracy
    try:
        result = do_decide(contract, org_id=body.org_id, payload=body.payload, budgets=budgets or None)
    except DomainError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=e.status_code, detail=e.message)
    out = {
        "action": {
            "class": result["class"],
            "reasons": result.get("reasons", []),
            "confidence": float(result.get("confidence", 0.5)),
            "required_docs": result.get("required_docs", []),
        },
        "decision_id": result["decision_id"],
    }
    return out
