from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.meter.collector import read_monthly
from apps.billing.calculator import calculate_invoice_items
from apps.billing.invoicer import close_month, INVOICES
from apps.billing.exporters.json import export_json
from apps.billing.exporters.pdf import export_pdf


router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class CloseBody(BaseModel):
    org_id: str
    yyyymm: str
    unit_price: float = 0.002
    metric: str = "decision_calls"


@router.post("/invoices/close")
def close_ep(body: CloseBody):
    usage = read_monthly(body.org_id, body.metric, body.yyyymm)
    # shape to include metric
    usage_lines = [{"metric": body.metric, **u} for u in usage]
    lines = calculate_invoice_items(usage_lines, body.unit_price)
    inv = close_month(body.org_id, body.yyyymm, lines)
    return inv


@router.get("/invoices/{invoice_id}")
def get_invoice_ep(invoice_id: str, fmt: str | None = None):
    inv = INVOICES.get(invoice_id)
    if not inv:
        raise HTTPException(404, "not found")
    if fmt == "json":
        return inv
    if fmt == "pdf":
        import base64
        return {"pdf_b64": base64.b64encode(export_pdf(inv)).decode("utf-8")}
    return inv


@router.get("/invoices")
def list_invoices_ep(org_id: str | None = None):
    items = list(INVOICES.values())
    if org_id:
        items = [i for i in items if i.get("org_id") == org_id]
    return items


