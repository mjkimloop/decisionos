from __future__ import annotations

from fastapi import APIRouter

from apps.gateway.middleware import metrics as metrics_mw
from apps.cost_sentry.sentry import summary as cost_summary
from apps.meter.summary import summary_monthly
from apps.tracing.context import get_corr_id


router = APIRouter(prefix="/api/v1/admin", tags=["admin"]) 


@router.get("/metrics")
def admin_metrics(org_id: str | None = None, period: str | None = None):
    data = {
        "app_metrics": metrics_mw.snapshot(),
        "cost_sentry": cost_summary(),
        "corr_id": get_corr_id(),
    }
    if org_id:
        data["usage_monthly"] = summary_monthly(org_id, period)
    return data

