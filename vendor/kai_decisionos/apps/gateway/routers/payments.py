from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.payments.gateway import record_payment, list_payments
from apps.payments.dunning import mark_overdue, schedule_followup, get_status
from apps.billing.reconciler import reconcile_invoice, get_reconciliation
from apps.payments.container import payments_service as _service
from apps.payments.adapters import list_adapters as local_payments_adapters
from apps.payments.state_machine import RefundState
from apps.common.idempotency import GLOBAL_IDEMPOTENCY_STORE
from apps.payments.webhooks import WebhookProcessor, map_event_to_state


router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
_webhooks = WebhookProcessor()



class IntentCreateBody(BaseModel):
    org_id: str
    amount: int
    currency: str = "KRW"
    customer_ref: str | None = None
    metadata: dict = Field(default_factory=dict)
    adapter: str = "manual_stub"


class IntentConfirmBody(BaseModel):
    intent_id: str
    payment_method: str


class CaptureBody(BaseModel):
    charge_id: str
    amount: int | None = None


class RefundBody(BaseModel):
    charge_id: str
    amount: int
    reason: str | None = None


class WebhookEnvelope(BaseModel):
    adapter: str
    headers: dict
    payload: str
    idempotency_key: str | None = None



@router.get("/adapters")
def list_supported_adapters():
    return {"adapters": list(local_payments_adapters())}

@router.post('/intent', status_code=201)
def create_intent(body: IntentCreateBody):
    try:
        intent = _service.create_intent(
            org_id=body.org_id,
            amount=body.amount,
            currency=body.currency,
            customer_ref=body.customer_ref,
            metadata=body.metadata,
            adapter_name=body.adapter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return intent.model_dump(mode="json")

@router.post('/confirm')
def confirm_intent(body: IntentConfirmBody):
    try:
        intent = _service.confirm_intent(body.intent_id, body.payment_method)
    except KeyError:
        raise HTTPException(status_code=404, detail="intent_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    charge = _service.latest_charge_for_intent(intent.id)
    return {
        "intent": intent.model_dump(mode="json"),
        "charge": charge.model_dump(mode="json") if charge else None,
    }

@router.post('/capture')
def capture(body: CaptureBody):
    try:
        charge = _service.capture_charge(body.charge_id, amount=body.amount)
    except KeyError:
        raise HTTPException(status_code=404, detail="charge_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return charge.model_dump(mode="json")

@router.post('/refund')
def refund(body: RefundBody):
    try:
        refund_obj = _service.refund_charge(body.charge_id, body.amount, reason=body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="charge_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return refund_obj.model_dump(mode="json")

@router.get('/charges/{charge_id}')
def get_charge(charge_id: str):
    try:
        charge = _service.get_charge(charge_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="charge_not_found")
    return charge.model_dump(mode="json")

@router.get('/receipts/{receipt_id}')
def get_receipt(receipt_id: str):
    try:
        receipt = _service.get_receipt(receipt_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    return receipt.model_dump(mode="json")

@router.post('/webhooks')
def handle_webhook(envelope: WebhookEnvelope):
    try:
        event = _webhooks.parse(envelope.adapter, envelope.headers, envelope.payload.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    key = envelope.idempotency_key or event.idempotency_key
    if GLOBAL_IDEMPOTENCY_STORE.get(key):
        return {"status": "duplicate"}
    payment_state, refund_state = map_event_to_state(event.event_type)
    if payment_state:
        charge_id = event.data.get("charge_id") or event.data.get("data", {}).get("charge_id")
        if charge_id:
            try:
                if payment_state == RefundState.REFUNDED:
                    pass
                else:
                    _service.post_settlement(charge_id)
            except KeyError:
                pass
    if refund_state:
        refund_id = event.data.get("refund_id") or event.data.get("data", {}).get("refund_id")
        if refund_id:
            try:
                _service.process_refund_update(refund_id, refund_state or RefundState.PENDING)
            except (KeyError, ValueError):
                pass
    GLOBAL_IDEMPOTENCY_STORE.set(key, {"event": event.event_type})
    return {"status": "processed", "event": event.event_type}

class PaymentBody(BaseModel):
    invoice_id: str
    amount: float
    method: str = "manual"
    status: str = "captured"


@router.post("/record")
def record_payment_ep(payload: PaymentBody):
    payment = record_payment(payload.invoice_id, payload.amount, payload.method, payload.status)
    return payment


@router.get("/ledger")
def list_payments_ep(invoice_id: str | None = None):
    return list_payments(invoice_id)


class DunningBody(BaseModel):
    invoice_id: str
    reason: str = "unpaid"
    channel: str = Field(default="email")
    eta: str | None = None


@router.post("/dunning")
def trigger_dunning(payload: DunningBody):
    record = mark_overdue(payload.invoice_id, payload.reason)
    if payload.eta:
        schedule_followup(payload.invoice_id, payload.channel, payload.eta)
    return record


@router.get("/dunning/{invoice_id}")
def get_dunning_ep(invoice_id: str):
    status = get_status(invoice_id)
    if not status:
        raise HTTPException(status_code=404, detail="no dunning record")
    return status


class ReconcileBody(BaseModel):
    invoice_id: str
    payment_id: str
    amount: float


@router.post("/reconcile")
def reconcile_ep(payload: ReconcileBody):
    try:
        record = reconcile_invoice(payload.invoice_id, payload.payment_id, payload.amount)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record


@router.get("/reconcile/{invoice_id}")
def get_reconcile_ep(invoice_id: str):
    record = get_reconciliation(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="not reconciled")
    return record
