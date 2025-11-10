from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from .invoicer import INVOICES

RECONCILIATIONS: Dict[str, dict] = {}


def reconcile_invoice(invoice_id: str, payment_id: str, amount: float) -> dict:
    invoice = INVOICES.get(invoice_id)
    if not invoice:
        raise KeyError("invoice_not_found")
    invoice["status"] = "paid"
    invoice["paid_at"] = datetime.now(timezone.utc).isoformat()
    record = {
        "invoice_id": invoice_id,
        "payment_id": payment_id,
        "amount": round(amount, 4),
        "reconciled_at": datetime.now(timezone.utc).isoformat(),
    }
    RECONCILIATIONS[invoice_id] = record
    return record


def get_reconciliation(invoice_id: str) -> Optional[dict]:
    return RECONCILIATIONS.get(invoice_id)


__all__ = ["reconcile_invoice", "get_reconciliation", "RECONCILIATIONS"]

