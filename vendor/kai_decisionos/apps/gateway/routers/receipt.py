from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.billing.invoicer import INVOICES
from apps.payments.container import payments_service
from apps.payments.models import Receipt
from apps.receipts.render import render_receipt_assets


router = APIRouter(prefix="/api/v1/receipt", tags=["receipt"])


class ReceiptIssueBody(BaseModel):
    invoice_id: str


@router.post("/issue")
def issue_receipt(body: ReceiptIssueBody):
    invoice = INVOICES.get(body.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    receipt = Receipt(
        charge_id=body.invoice_id,
        org_id=invoice.get("org_id", "unknown"),
        total=int(invoice.get("total", 0)),
        currency=invoice.get("currency", "KRW"),
        issued_at=datetime.now(timezone.utc),
        tax_amount=int(invoice.get("tax", 0)),
    )
    pdf_uri, json_uri = render_receipt_assets(receipt.model_dump(mode="json"))
    receipt.pdf_uri = pdf_uri
    receipt.json_uri = json_uri
    payments_service.repo.receipts[receipt.id] = receipt
    return {"receipt_id": receipt.id, "pdf_url": pdf_uri, "json_url": json_uri}


__all__ = ["router"]
