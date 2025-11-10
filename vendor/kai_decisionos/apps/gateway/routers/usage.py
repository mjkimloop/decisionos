from __future__ import annotations

from fastapi import APIRouter

from apps.meter.collector import read_daily, read_monthly


router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get("/daily")
def daily(org_id: str, metric: str, frm: str | None = None, to: str | None = None):
    return {"org_id": org_id, "metric": metric, "items": read_daily(org_id, metric, frm, to)}


@router.get("/monthly")
def monthly(org_id: str, metric: str, yyyymm: str | None = None):
    return {"org_id": org_id, "metric": metric, "items": read_monthly(org_id, metric, yyyymm)}

