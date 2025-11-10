from __future__ import annotations

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from apps.catalog.boundaries import BoundaryViolation, evaluate_boundary, list_events
from apps.catalog.tags import get_tags

router = APIRouter(prefix="/api/v1/boundaries", tags=["boundaries"])


@router.get("/check")
def boundary_check(
    dataset: str = Query(..., description="Dataset identifier in the catalog"),
    org_id: str = Query(..., description="Organisation identifier (region:org-slug)"),
    target_region: str | None = Query(None, description="Override target region (defaults to org region)"),
    purpose: str | None = Query(None, description="Purpose binding for export requests"),
    ticket_id: str | None = Query(None, description="Change-management / approval ticket reference"),
    retention_days: int | None = Query(None, description="Requested retention days for exported copy"),
):
    try:
        result = evaluate_boundary(
            dataset,
            org_id=org_id,
            target_region=target_region,
            purpose=purpose,
            ticket_id=ticket_id,
            retention_days=retention_days,
        )
        return {
            "status": result.status,
            "enforced_controls": result.enforced_controls,
            "tags": result.tags,
        }
    except BoundaryViolation as exc:
        payload = {
            "error": exc.reason,
            "required_controls": exc.required_controls,
        }
        if exc.event:
            payload["event"] = exc.event.to_dict()
        raise HTTPException(status_code=403, detail=payload) from exc


@router.get("/alerts")
def boundary_alerts():
    return {"items": list_events()}


__all__ = ["router"]
