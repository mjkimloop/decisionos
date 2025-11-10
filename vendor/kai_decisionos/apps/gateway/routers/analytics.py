from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from apps.events.sdk import track_event
from apps.analytics.service import summarise_events, dashboard_html, summary_counts


router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class EventPayload(BaseModel):
    event: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = Field(default="api")
    metadata: dict = Field(default_factory=dict)


@router.post("/events", status_code=201)
def ingest_event(payload: EventPayload):
    evt = track_event(
        payload.event,
        user_id=payload.user_id,
        session_id=payload.session_id,
        source=payload.source,
        metadata=payload.metadata,
    )
    return {"event": evt.event, "created_at": evt.created_at}


@router.post("/events/batch", status_code=201)
def ingest_batch(payload: List[EventPayload]):
    if not payload:
        raise HTTPException(status_code=400, detail="payload empty")
    for item in payload:
        ingest_event(item)
    return {"accepted": len(payload)}


@router.get("/summary")
def analytics_summary(limit: Optional[int] = None):
    return summarise_events(limit=limit)


@router.get("/counts")
def analytics_counts():
    return summary_counts()


@router.get("/dashboard", response_class=HTMLResponse)
def analytics_dashboard(limit: Optional[int] = None):
    summary = summarise_events(limit=limit)
    return HTMLResponse(content=dashboard_html(summary))

