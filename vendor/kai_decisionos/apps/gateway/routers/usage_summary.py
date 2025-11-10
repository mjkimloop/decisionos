from __future__ import annotations

from fastapi import APIRouter

from apps.meter.summary import summary_monthly

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get("/summary")
def get_summary(org_id: str, period: str | None = None):
    return summary_monthly(org_id, period)
