from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


PAYMENTS: Dict[str, dict] = {}


def record_payment(invoice_id: str, amount: float, method: str = "manual", status: str = "captured") -> dict:
    payment_id = f"pay_{len(PAYMENTS) + 1:04d}"
    record = {
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount": round(amount, 4),
        "method": method,
        "status": status,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    PAYMENTS[payment_id] = record
    try:
        from apps.billing.invoicer import INVOICES  # local import to avoid cycle

        invoice = INVOICES.get(invoice_id)
        if invoice:
            invoice["balance_due"] = round(max(invoice.get("balance_due", invoice.get("total", 0.0)) - record["amount"], 0.0), 4)
            if invoice["balance_due"] <= 0:
                invoice["status"] = "paid"
                invoice["paid_at"] = record["recorded_at"]
    except Exception:
        pass
    return record


def list_payments(invoice_id: Optional[str] = None) -> List[dict]:
    values = list(PAYMENTS.values())
    if invoice_id:
        values = [p for p in values if p.get("invoice_id") == invoice_id]
    return values


__all__ = ["record_payment", "list_payments", "PAYMENTS"]
