from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from .registry import register_adapter
from .types import AdapterResult, IPayAdapter, captured_charge
from ..models import Charge, PaymentIntent, Refund
from ..state_machine import PaymentState, RefundState


class StripeStubAdapter(IPayAdapter):
    name = "stripe_stub"

    def authorize(self, intent: PaymentIntent, payment_method: str) -> AdapterResult:
        if payment_method.startswith("tok_fail"):
            return AdapterResult(state=PaymentState.FAILED, error="card_declined")
        if payment_method.startswith("tok_3ds"):
            return AdapterResult(state=PaymentState.REQUIRES_ACTION, requires_action=True)
        charge = Charge(
            intent_id=intent.id,
            amount=intent.amount,
            currency=intent.currency,
            adapter=self.name,
            state=PaymentState.AUTHORIZED,
        )
        return AdapterResult(state=PaymentState.AUTHORIZED, charge=charge)

    def capture(self, intent: PaymentIntent, charge: Charge, amount: int) -> Charge:
        if amount > intent.amount:
            raise ValueError("capture_amount_exceeds_intent")
        charge = captured_charge(charge, amount)
        return charge

    def refund(self, intent: PaymentIntent, charge: Charge, amount: int, reason: str | None = None) -> Refund:
        if amount > charge.amount:
            raise ValueError("refund_amount_exceeds_charge")
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
        signature = headers.get("Stripe-Signature")
        if not signature or not signature.startswith("t="):
            raise ValueError("invalid_signature")
        event = json.loads(payload.decode("utf-8"))
        event.setdefault("idempotency_key", secrets.token_hex(8))
        return event


register_adapter(StripeStubAdapter.name, StripeStubAdapter())

__all__ = ["StripeStubAdapter"]
