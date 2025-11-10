from __future__ import annotations

from fastapi import APIRouter

from apps.billing.invoicer import INVOICES
from apps.cost_guard.margin import compute_margin
from apps.cost_guard.alerts import check_margin_alert


router = APIRouter(prefix="/api/v1/ops/cost-guard", tags=["ops"]) 


@router.get("")
def report(yyyymm: str | None = None):
    # naive: sum invoices
    billed = 0.0
    for inv in INVOICES.values():
        if yyyymm is None or inv.get("period") == yyyymm:
            billed += float(inv.get("total", 0.0))
    # dev: constant costs
    model_cost = 0.0
    infra_cost = billed * 0.2  # pretend 20% infra cost
    m = compute_margin(billed, model_cost, infra_cost)
    alert = check_margin_alert(m["margin_pct"])  # type: ignore[index]
    return {"billed_total": round(billed, 4), **m, **alert}

