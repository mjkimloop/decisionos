from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from .registry import register_adapter
from .types import AdapterResult, IPayAdapter, captured_charge
from ..models import Charge, PaymentIntent, Refund
from ..state_machine import PaymentState, RefundState


class GenericPGAdapter(IPayAdapter):
    name = "generic_pg"

    def __init__(self, secret: str | None = None) -> None:
        self.secret = secret or "generic-secret"

    def authorize(self, intent: PaymentIntent, payment_method: str) -> AdapterResult:
        charge = Charge(
            intent_id=intent.id,
            amount=intent.amount,
            currency=intent.currency,
            adapter=self.name,
            state=PaymentState.AUTHORIZED,
        )
        return AdapterResult(state=PaymentState.AUTHORIZED, charge=charge)

    def capture(self, intent: PaymentIntent, charge: Charge, amount: int) -> Charge:
        charge = captured_charge(charge, amount)
        return charge

    def refund(self, intent: PaymentIntent, charge: Charge, amount: int, reason: str | None = None) -> Refund:
        refund = Refund(
            charge_id=charge.id,
            amount=amount,
            currency=charge.currency,
            reason=reason,
        )
        refund.state = RefundState.REFUNDED
        refund.processed_at = datetime.now(timezone.utc)
        return refund

    def void(self, intent: PaymentIntent) -> AdapterResult:
        return AdapterResult(state=PaymentState.CANCELED)

    def verify_webhook(self, headers: dict, payload: bytes) -> dict:
        signature = headers.get("X-PG-Signature")
        timestamp = headers.get("X-PG-Timestamp")
        if not signature or not timestamp:
            raise ValueError("missing_headers")
        body = payload.decode("utf-8")
        expected = hmac.new(self.secret.encode("utf-8"), msg=f"{timestamp}.{body}".encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("invalid_signature")
        event = json.loads(body)
        event["verified_at"] = datetime.now(tz=timezone.utc).isoformat()
        return event


register_adapter(GenericPGAdapter.name, GenericPGAdapter())

__all__ = ["GenericPGAdapter"]
