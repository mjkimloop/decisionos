from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from ..models import Charge, PaymentIntent, Refund
from ..state_machine import PaymentState, RefundState


@dataclass
class AdapterResult:
    state: PaymentState
    charge: Charge | None = None
    requires_action: bool = False
    error: str | None = None


class IPayAdapter(Protocol):
    name: str

    def authorize(self, intent: PaymentIntent, payment_method: str) -> AdapterResult:
        ...

    def capture(self, intent: PaymentIntent, charge: Charge, amount: int) -> Charge:
        ...

    def refund(self, intent: PaymentIntent, charge: Charge, amount: int, reason: str | None = None) -> Refund:
        ...

    def void(self, intent: PaymentIntent) -> AdapterResult:
        ...

    def verify_webhook(self, headers: dict, payload: bytes) -> dict:
        ...


def captured_charge(base: Charge, amount: int) -> Charge:
    base.amount = amount
    base.state = PaymentState.CAPTURED
    base.captured_at = datetime.now(timezone.utc)
    return base


__all__ = ["AdapterResult", "IPayAdapter", "captured_charge"]
