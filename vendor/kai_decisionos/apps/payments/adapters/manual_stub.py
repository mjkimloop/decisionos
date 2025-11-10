from __future__ import annotations

from datetime import datetime, timezone

from .registry import register_adapter
from .types import AdapterResult, IPayAdapter, captured_charge
from ..models import Charge, PaymentIntent, Refund
from ..state_machine import PaymentState, RefundState


class ManualAdapter(IPayAdapter):
    name = "manual_stub"

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
        return {"event": "manual_stub", "payload": payload.decode("utf-8")}


register_adapter(ManualAdapter.name, ManualAdapter())


__all__ = ["ManualAdapter"]
