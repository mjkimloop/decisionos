from __future__ import annotations

from datetime import UTC, datetime
from fastapi import APIRouter

from apps.hitl.models import CASES


router = APIRouter(prefix="/api/v1/sla", tags=["sla"])


@router.get("/report")
def sla_report(frm: str | None = None, to: str | None = None):
    # very naive counters
    now = datetime.now(UTC)
    total = len(CASES)
    breached = sum(1 for c in CASES.values() if c.sla_due_at and c.sla_due_at < now and c.status != "closed")
    return {"total_cases": total, "breaches": breached}
