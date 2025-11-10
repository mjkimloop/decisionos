from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .models import Charge, PaymentIntent, Receipt, Refund
from .state_machine import (
    InvalidTransition,
    PaymentState,
    RefundState,
    transition_payment,
    transition_refund,
)
from .adapters.registry import get_adapter, list_adapters
from .receipts import generate_receipt


@dataclass
class PaymentsRepository:
    intents: Dict[str, PaymentIntent]
    charges: Dict[str, Charge]
    refunds: Dict[str, Refund]
    receipts: Dict[str, Receipt]


class PaymentsService:
    def __init__(self, repo: Optional[PaymentsRepository] = None) -> None:
        self.repo = repo or PaymentsRepository(intents={}, charges={}, refunds={}, receipts={})

    def create_intent(
        self,
        *,
        org_id: str,
        amount: int,
        currency: str,
        customer_ref: str | None,
        metadata: dict,
        adapter_name: str,
    ) -> PaymentIntent:
        if adapter_name not in list_adapters():
            raise ValueError(f"unknown_adapter:{adapter_name}")
        intent = PaymentIntent(
            org_id=org_id,
            amount=amount,
            currency=currency,
            customer_ref=customer_ref,
            metadata=metadata,
            adapter=adapter_name,
        )
        self.repo.intents[intent.id] = intent
        return intent

    def confirm_intent(self, intent_id: str, payment_method: str) -> PaymentIntent:
        intent = self._require_intent(intent_id)
        adapter = get_adapter(intent.adapter)
        result = adapter.authorize(intent, payment_method=payment_method)
        try:
            intent.state = transition_payment(intent.state, result.state)
        except InvalidTransition as exc:  # pragma: no cover - adapter contract bug
            raise ValueError(str(exc)) from exc
        intent.payment_method = payment_method
        self.repo.intents[intent.id] = intent
        if result.charge:
            self.repo.charges[result.charge.id] = result.charge
        return intent

    def capture_charge(self, charge_id: str, amount: int | None = None) -> Charge:
        charge = self._require_charge(charge_id)
        intent = self._require_intent(charge.intent_id)
        adapter = get_adapter(intent.adapter)
        desired_amount = amount or charge.amount
        result_charge = adapter.capture(intent, charge, desired_amount)
        try:
            intent.state = transition_payment(intent.state, result_charge.state)
            charge.state = result_charge.state
        except InvalidTransition as exc:
            raise ValueError(str(exc)) from exc
        charge.captured_at = result_charge.captured_at
        self.repo.charges[charge.id] = charge
        self.repo.intents[intent.id] = intent
        if charge.state == PaymentState.CAPTURED:
            receipt = generate_receipt(intent, charge)
            charge.receipt_id = receipt.id
            self.repo.receipts[receipt.id] = receipt
        return charge

    def refund_charge(self, charge_id: str, amount: int, reason: str | None = None) -> Refund:
        charge = self._require_charge(charge_id)
        intent = self._require_intent(charge.intent_id)
        adapter = get_adapter(intent.adapter)
        refund = adapter.refund(intent, charge, amount, reason=reason)
        self.repo.refunds[refund.id] = refund
        return refund

    def process_refund_update(self, refund_id: str, target_state: RefundState) -> Refund:
        refund = self._require_refund(refund_id)
        refund.state = transition_refund(refund.state, target_state)
        self.repo.refunds[refund.id] = refund
        return refund

    def post_settlement(self, charge_id: str) -> Charge:
        charge = self._require_charge(charge_id)
        charge.state = PaymentState.SETTLED
        self.repo.charges[charge.id] = charge
        intent = self._require_intent(charge.intent_id)
        intent.state = PaymentState.SETTLED
        self.repo.intents[intent.id] = intent
        return charge

    def get_charge(self, charge_id: str) -> Charge:
        return self._require_charge(charge_id)

    def get_receipt(self, receipt_id: str) -> Receipt:
        if receipt_id not in self.repo.receipts:
            raise KeyError("receipt_not_found")
        return self.repo.receipts[receipt_id]

    def _require_intent(self, intent_id: str) -> PaymentIntent:
        if intent_id not in self.repo.intents:
            raise KeyError("intent_not_found")
        return self.repo.intents[intent_id]

    def _require_charge(self, charge_id: str) -> Charge:
        if charge_id not in self.repo.charges:
            raise KeyError("charge_not_found")
        return self.repo.charges[charge_id]

    def _require_refund(self, refund_id: str) -> Refund:
        if refund_id not in self.repo.refunds:
            raise KeyError("refund_not_found")
        return self.repo.refunds[refund_id]

    def latest_charge_for_intent(self, intent_id: str) -> Charge | None:
        relevant = [charge for charge in self.repo.charges.values() if charge.intent_id == intent_id]
        if not relevant:
            return None
        return sorted(relevant, key=lambda c: c.created_at)[-1]


__all__ = ["PaymentsService", "PaymentsRepository"]
