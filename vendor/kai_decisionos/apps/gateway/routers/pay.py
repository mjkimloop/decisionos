from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel, Field

from apps.payments.adapters import list_adapters
from apps.payments.container import gateway_service, payments_service
from apps.payments.service import ChargeResult, RefundResult
from apps.payments.webhooks import WebhookProcessor, map_event_to_state
from apps.common.idempotency import GLOBAL_IDEMPOTENCY_STORE
from apps.payments.state_machine import RefundState
from apps.payments.dunning import mark_overdue, schedule_followup, get_status
from apps.payments.chargebacks import upsert_chargeback, list_chargebacks


router = APIRouter(prefix="/api/v1/pay", tags=["payments"])
_webhooks = WebhookProcessor()


class ChargeRequest(BaseModel):
    org_id: str | None = None
    invoice_id: str | None = None
    amount: int | None = None
    currency: str | None = None
    payment_token: str | None = None
    payment_intent: str | None = None
    adapter: str = "stripe_stub"
    metadata: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class RefundRequest(BaseModel):
    charge_id: str
    amount: int | None = None
    reason: str | None = None


class DunningRunRequest(BaseModel):
    org_id: str | None = None
    invoice_id: str | None = None
    channel: str = "email"
    schedule: list[dict] = Field(default_factory=list)


class ChargebackUpdate(BaseModel):
    psp_ref: str
    stage: str
    amount: int
    reason: str | None = None
    evidence_url: str | None = None
    currency: str = "KRW"


class WebhookBody(BaseModel):
    headers: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)


@router.get("/adapters")
def pay_adapters():
    return {"adapters": list(list_adapters())}


@router.post("/charge")
def create_charge(
    payload: dict = Body(...),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    normalized = _normalize_charge_payload(payload)
    body = ChargeRequest.model_validate(normalized)
    payment_method = body.payment_token
    try:
        result = gateway_service.charge(
            org_id=body.org_id,
            invoice_id=body.invoice_id,
            amount=body.amount,
            currency=body.currency,
            payment_method=payment_method,
            payment_intent_id=body.payment_intent,
            adapter=body.adapter,
            metadata=body.metadata,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_charge_result(result)


@router.post("/refund")
def refund_charge(
    body: RefundRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    try:
        result = gateway_service.refund(
            charge_id=body.charge_id,
            amount=body.amount,
            reason=body.reason,
            idempotency_key=idempotency_key,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="charge_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"refund": result.refund, "status": result.status}


@router.post("/dunning/run")
def run_dunning(body: DunningRunRequest, idempotency_key: str = Header(..., alias="Idempotency-Key")):
    existing = GLOBAL_IDEMPOTENCY_STORE.get(f"dunning:{idempotency_key}")
    if existing:
        return existing.response
    if not body.invoice_id:
        raise HTTPException(status_code=400, detail="invoice_id_required")
    record = mark_overdue(body.invoice_id, reason="unpaid", org_id=body.org_id)
    for followup in body.schedule or []:
        channel = followup.get("channel", body.channel)
        eta = followup.get("eta")
        if eta:
            schedule_followup(body.invoice_id, channel, eta)
    status = get_status(body.invoice_id)
    GLOBAL_IDEMPOTENCY_STORE.set(f"dunning:{idempotency_key}", status or record)
    return status or record


@router.post("/chargeback/update")
def update_chargeback(body: ChargebackUpdate, idempotency_key: str = Header(..., alias="Idempotency-Key")):
    record = upsert_chargeback(
        idempotency_key=idempotency_key,
        psp_ref=body.psp_ref,
        stage=body.stage,
        amount=body.amount,
        currency=body.currency,
        reason=body.reason,
        evidence_url=body.evidence_url,
    )
    return record


@router.get("/chargeback")
def list_chargeback_records():
    return {"items": list_chargebacks()}


@router.post("/webhook/{adapter}")
def handle_webhook(adapter: str, body: WebhookBody, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    try:
        event = _webhooks.parse(adapter, body.headers, json_bytes(body.payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    key = idempotency_key or event.idempotency_key
    if GLOBAL_IDEMPOTENCY_STORE.get(f"webhook:{key}"):
        return {"status": "duplicate"}
    payment_state, refund_state = map_event_to_state(event.event_type)
    if payment_state:
        charge_id = event.data.get("charge_id") or event.data.get("data", {}).get("charge_id")
        if charge_id and payment_state != RefundState.REFUNDED:
            try:
                payments_service.post_settlement(charge_id)
            except KeyError:
                pass
    if refund_state:
        refund_id = event.data.get("refund_id") or event.data.get("data", {}).get("refund_id")
        if refund_id:
            try:
                payments_service.process_refund_update(refund_id, refund_state)
            except (KeyError, ValueError):
                pass
    GLOBAL_IDEMPOTENCY_STORE.set(f"webhook:{key}", {"status": "processed"})
    return {"status": "processed"}


def _serialize_charge_result(result: ChargeResult) -> dict:
    payload = {
        "intent": result.intent,
        "status": result.status,
    }
    if result.charge:
        payload["charge"] = result.charge
    if result.receipt:
        payload["receipt"] = result.receipt
    return payload


def json_bytes(payload: dict) -> bytes:
    import json

    return json.dumps(payload).encode("utf-8")


def _normalize_charge_payload(payload: dict) -> dict:
    data = dict(payload or {})
    if "payment_token" not in data:
        for key in ("pm_id", "payment_method"):
            if key in data and data[key]:
                data["payment_token"] = data[key]
                break
    return data


__all__ = ["router"]
