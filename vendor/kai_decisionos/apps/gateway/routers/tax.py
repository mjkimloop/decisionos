from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.billing.invoicer import INVOICES
from apps.tax import get_adapter


router = APIRouter(prefix="/api/v1/tax", tags=["tax"])
ADAPTER = get_adapter()


class TaxCalcBody(BaseModel):
    invoice_id: str | None = None
    amount: int | None = None
    currency: str | None = None
    lines: list[dict] = Field(default_factory=list)
    country: str = "KR"
    category: str = "default"
    tax_exempt: bool = False


@router.post("/calc")
def calculate_tax(body: TaxCalcBody):
    amount = body.amount
    if body.invoice_id:
        invoice = INVOICES.get(body.invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="invoice_not_found")
        amount = amount or int(invoice.get("subtotal", invoice.get("total", 0)))
        body.currency = body.currency or invoice.get("currency", "KRW")
    if amount is None:
        amount = sum(int(line.get("amount", 0)) for line in body.lines)
    comp = ADAPTER.calculate(
        amount=amount,
        country=body.country,
        category=body.category,
        tax_exempt=body.tax_exempt,
        metadata={"invoice_id": body.invoice_id},
    )
    data = comp.model_dump()
    data["amount"] = amount
    data["currency"] = body.currency or data["currency"]
    return data


__all__ = ["router"]
