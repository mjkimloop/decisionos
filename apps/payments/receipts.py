from __future__ import annotations

from pathlib import Path

from apps.taxes.rules import calculate_tax, load_rules
from apps.common.timeutil import time_utcnow
from .models import Charge, PaymentIntent, Receipt

RULES = load_rules(Path("configs/region_rules.yaml"))


def generate_receipt(intent: PaymentIntent, charge: Charge, region_code: str = "KR") -> Receipt:
    tax_amount = calculate_tax(charge.amount, region_code=region_code, rules=RULES, category="default")
    receipt = Receipt(
        charge_id=charge.id,
        org_id=intent.org_id,
        total=charge.amount,
        currency=charge.currency,
        issued_at=time_utcnow(),
        tax_amount=tax_amount,
    )
    # dev placeholder for PDF/JSON URIs
    receipt.pdf_uri = f"var/receipts/{receipt.id}.pdf"
    receipt.json_uri = f"var/receipts/{receipt.id}.json"
    return receipt


__all__ = ["generate_receipt"]
