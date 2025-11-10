from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from apps.common.idempotency import GLOBAL_IDEMPOTENCY_STORE
from apps.billing.invoicer import INVOICES
from apps.ledger.postings import post_double_entry
from .core import PaymentsRepository, PaymentsService
from .state_machine import PaymentState


@dataclass
class ChargeResult:
    intent: dict
    charge: dict | None
    receipt: dict | None
    status: str


@dataclass
class RefundResult:
    refund: dict
    status: str


class PaymentGatewayService:
    """High level charge/refund orchestration with idempotency and invoice awareness."""

    def __init__(self, payments_service: Optional[PaymentsService] = None) -> None:
        if payments_service:
            self.payments = payments_service
            self.repo = payments_service.repo
        else:
            self.repo = PaymentsRepository({}, {}, {}, {})
            self.payments = PaymentsService(self.repo)

    def _resolve_invoice(self, invoice_id: Optional[str]) -> Optional[dict]:
        if not invoice_id:
            return None
        return INVOICES.get(invoice_id)

    def charge(
        self,
        *,
        org_id: Optional[str],
        invoice_id: Optional[str],
        amount: Optional[int],
        currency: Optional[str],
        payment_method: Optional[str],
        payment_intent_id: Optional[str],
        adapter: str,
        metadata: Optional[Dict[str, Any]],
        idempotency_key: str,
    ) -> ChargeResult:
        existing = GLOBAL_IDEMPOTENCY_STORE.get(idempotency_key)
        if existing:
            payload = existing.response
            return ChargeResult(
                intent=payload["intent"],
                charge=payload.get("charge"),
                receipt=payload.get("receipt"),
                status=payload["status"],
            )

        invoice = self._resolve_invoice(invoice_id)
        if invoice:
            amount = amount or int(invoice.get("balance_due") or invoice.get("total") or 0)
            currency = currency or invoice.get("currency", "KRW")
            org_id = org_id or invoice.get("org_id")
        if not org_id:
            raise ValueError("org_id_required")
        if amount is None:
            raise ValueError("amount_required")
        if amount <= 0:
            raise ValueError("amount_invalid")
        currency = currency or "KRW"
        metadata = metadata or {}
        if payment_intent_id:
            intent = self.payments.get_intent(payment_intent_id)
            if intent.adapter != adapter and adapter:
                raise ValueError("adapter_mismatch")
            org_id = intent.org_id
            amount = intent.amount
            currency = intent.currency
        else:
            intent = self.payments.create_intent(
                org_id=org_id,
                amount=amount,
                currency=currency,
                customer_ref=metadata.get("customer_ref"),
                metadata=metadata,
                adapter_name=adapter,
            )
        payment_method = payment_method or "pm_test"
        intent = self.payments.confirm_intent(intent.id, payment_method=payment_method)
        charge = self.payments.latest_charge_for_intent(intent.id)
        receipt_dict: dict | None = None
        charge_dict: dict | None = charge.model_dump(mode="json") if charge else None
        status = intent.state.value
        if intent.state == PaymentState.AUTHORIZED and charge:
            charge = self.payments.capture_charge(charge.id)
            status = charge.state.value
            charge_dict = charge.model_dump(mode="json")
            if charge.receipt_id:
                receipt = self.payments.get_receipt(charge.receipt_id)
                receipt_dict = receipt.model_dump(mode="json")
                if invoice:
                    invoice["balance_due"] = max(0, invoice.get("balance_due", amount) - charge.amount)
                    if invoice["balance_due"] == 0:
                        invoice["status"] = "paid"
        payload = {
            "intent": intent.model_dump(mode="json"),
            "charge": charge_dict,
            "receipt": receipt_dict,
            "status": status,
        }
        if charge_dict and receipt_dict:
            self._post_charge_ledger(charge_dict, receipt_dict)
        GLOBAL_IDEMPOTENCY_STORE.set(idempotency_key, payload)
        return ChargeResult(
            intent=payload["intent"],
            charge=payload["charge"],
            receipt=payload["receipt"],
            status=status,
        )

    def refund(
        self,
        *,
        charge_id: str,
        amount: Optional[int],
        reason: Optional[str],
        idempotency_key: str,
    ) -> RefundResult:
        existing = GLOBAL_IDEMPOTENCY_STORE.get(idempotency_key)
        if existing:
            payload = existing.response
            return RefundResult(refund=payload["refund"], status=payload["status"])
        charge_model = self.payments.get_charge(charge_id)
        refund_amount = amount or charge_model.amount
        refund = self.payments.refund_charge(charge_id, refund_amount, reason=reason)
        refund_dict = refund.model_dump(mode="json")
        self._post_refund_ledger(charge_model.model_dump(mode="json"), refund_dict)
        payload = {"refund": refund_dict, "status": refund.state.value}
        GLOBAL_IDEMPOTENCY_STORE.set(idempotency_key, payload)
        return RefundResult(refund=payload["refund"], status=refund.state.value)

    def _post_charge_ledger(self, charge: dict, receipt: dict) -> None:
        amount = int(charge.get("amount", 0))
        currency = charge.get("currency", "KRW")
        tax_amount = int(receipt.get("tax_amount", 0))
        revenue = max(amount - tax_amount, 0)
        entries = [
            {"account": "Cash", "debit": amount, "currency": currency, "ref": charge.get("id")},
        ]
        if revenue:
            entries.append({"account": "Revenue", "credit": revenue, "currency": currency, "ref": charge.get("id")})
        if tax_amount:
            entries.append({"account": "TaxPayable", "credit": tax_amount, "currency": currency, "ref": charge.get("id")})
        post_double_entry(entries)

    def _post_refund_ledger(self, charge: dict, refund: dict) -> None:
        amount = int(refund.get("amount", 0))
        currency = refund.get("currency", charge.get("currency", "KRW"))
        tax_amount = 0
        receipt_id = charge.get("receipt_id")
        if receipt_id:
            receipt = self.payments.get_receipt(receipt_id)
            if receipt.total:
                ratio = receipt.tax_amount / receipt.total
                tax_amount = int(round(amount * ratio))
            else:
                tax_amount = int(receipt.tax_amount)
        net_amount = max(amount - tax_amount, 0)
        entries = []
        if net_amount:
            entries.append({"account": "Refunds", "debit": net_amount, "currency": currency, "ref": refund.get("id")})
        if tax_amount:
            entries.append({"account": "TaxPayable", "debit": tax_amount, "currency": currency, "ref": refund.get("id")})
        entries.append({"account": "Cash", "credit": amount, "currency": currency, "ref": refund.get("id")})
        post_double_entry(entries)


__all__ = ["PaymentGatewayService", "ChargeResult", "RefundResult"]
