from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from apps.payments.container import payments_service
from apps.reconcile.pending_queue import add_pending, list_pending


@dataclass
class MatchResult:
    charge_id: str
    invoice_id: Optional[str]
    matched: bool
    variance: int = 0
    currency: str = "KRW"
    meta: Dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "charge_id": self.charge_id,
            "invoice_id": self.invoice_id,
            "matched": self.matched,
            "variance": self.variance,
            "currency": self.currency,
            "meta": self.meta,
        }


MATCHES: List[dict] = []


def reconcile_charge_event(event: dict) -> MatchResult:
    charge_id = event.get("charge_id")
    amount = int(event.get("amount", 0))
    currency = event.get("currency", "KRW")
    charge = payments_service.repo.charges.get(charge_id)
    if not charge:
        add_pending(charge_id, {"reason": "missing_charge", "event": event})
        return MatchResult(charge_id=charge_id, invoice_id=None, matched=False, variance=amount, currency=currency)
    variance = amount - charge.amount
    if variance != 0:
        add_pending(charge_id, {"reason": "amount_mismatch", "variance": variance, "event": event})
        result = MatchResult(
            charge_id=charge_id,
            invoice_id=None,
            matched=False,
            variance=variance,
            currency=currency,
        )
    else:
        result = MatchResult(
            charge_id=charge_id,
            invoice_id=charge.receipt_id,
            matched=True,
            variance=0,
            currency=currency,
        )
    MATCHES.append(result.as_dict())
    return result


def reconciliation_status() -> dict:
    matched = [m for m in MATCHES if m["matched"]]
    unmatched = [m for m in MATCHES if not m["matched"]]
    return {
        "matched": len(matched),
        "unmatched": len(unmatched),
        "pending": list_pending(),
    }


__all__ = ["reconcile_charge_event", "reconciliation_status", "MATCHES"]
