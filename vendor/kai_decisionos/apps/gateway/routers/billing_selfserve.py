from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.billing.selfserve import subscribe, get_subscription, list_subscriptions
from apps.billing.ratebook import list_plans, get_unit_price, clear_cache


router = APIRouter(prefix="/api/v1/billing/selfserve", tags=["billing-selfserve"])


class SubscribeBody(BaseModel):
    org_id: str
    plan: str
    effective_at: str | None = None


@router.post("/subscribe")
def subscribe_ep(payload: SubscribeBody):
    try:
        record = subscribe(payload.org_id, payload.plan, payload.effective_at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record


@router.get("/subscription/{org_id}")
def subscription_ep(org_id: str):
    record = get_subscription(org_id)
    if not record:
        raise HTTPException(status_code=404, detail="not subscribed")
    return record


@router.get("/ratebook")
def ratebook_ep():
    clear_cache()
    return list_plans()


@router.get("/rate/{plan}/{metric}")
def rate_lookup(plan: str, metric: str):
    price = get_unit_price(plan, metric)
    return {"plan": plan, "metric": metric, "price": price}


@router.get("/subscriptions")
def subscriptions_ep():
    return list_subscriptions()
