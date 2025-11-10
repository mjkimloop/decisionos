from __future__ import annotations

from datetime import datetime, timezone

from apps.tax import get_adapter
from apps.receipts.render import render_receipt_assets
from .models import Charge, PaymentIntent, Receipt

TAX = get_adapter()


def generate_receipt(intent: PaymentIntent, charge: Charge, country_code: str = "KR") -> Receipt:
    metadata = intent.metadata or {}
    tax_info = TAX.calculate(
        amount=charge.amount,
        country=metadata.get("tax_country", country_code),
        category=metadata.get("tax_category", "default"),
        tax_exempt=metadata.get("tax_exempt", False),
        metadata={"invoice_id": metadata.get("invoice_id")},
    )
    receipt = Receipt(
        charge_id=charge.id,
        org_id=intent.org_id,
        total=charge.amount,
        currency=charge.currency,
        issued_at=datetime.now(timezone.utc),
        tax_amount=tax_info.tax_total,
    )
    pdf_uri, json_uri = render_receipt_assets(receipt.model_dump(mode="json"))
    receipt.pdf_uri = pdf_uri
    receipt.json_uri = json_uri
    return receipt


__all__ = ["generate_receipt"]
