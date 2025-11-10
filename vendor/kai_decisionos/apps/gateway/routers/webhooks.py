from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.ext.webhooks.verify import verify_webhook

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

_SUBSCRIPTIONS: Dict[str, List[dict]] = {}
_COUNTER = 0


class SubscribeBody(BaseModel):
    event: str
    target_url: str
    secret: str


@router.post("/subscribe", status_code=201)
def subscribe(body: SubscribeBody):
    global _COUNTER
    _COUNTER += 1
    record = {"id": f"sub_{_COUNTER:05d}", **body.model_dump()}
    _SUBSCRIPTIONS.setdefault(body.event, []).append(record)
    return record


@router.get("/subscribe")
def list_subscriptions(event: str | None = None):
    if event:
        return _SUBSCRIPTIONS.get(event, [])
    all_records: List[dict] = []
    for evt, records in _SUBSCRIPTIONS.items():
        for record in records:
            all_records.append({"event": evt, **record})
    return all_records


@router.delete("/subscribe/{subscription_id}", status_code=204)
def delete_subscription(subscription_id: str):
    for records in _SUBSCRIPTIONS.values():
        for idx, record in enumerate(records):
            if record["id"] == subscription_id:
                records.pop(idx)
                return
    raise HTTPException(status_code=404, detail="subscription_not_found")


class DeliverBody(BaseModel):
    event: str
    headers: dict
    payload: str
    secret: str


@router.post("/deliver")
def deliver(body: DeliverBody):
    verify_webhook(body.headers, body.payload.encode("utf-8"), body.secret)
    return {"status": "verified"}


__all__ = ["router"]
