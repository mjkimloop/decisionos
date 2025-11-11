from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os

router = APIRouter()

# Mock RBAC for now - will integrate with existing RBAC system
def require_scope(scope: str):
    def dependency():
        # In production, this would validate RBAC token
        return True
    return dependency

class AggregateReq(BaseModel):
    reasons: List[str] = Field(default_factory=list)
    top: int = 5

@router.get("/cards/reason-trends/palette")
def get_palette(_=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, etag_seed
    return {"seed": etag_seed(), "palette": palette_with_desc()}

@router.post("/cards/reason-trends")
def post_trends(req: AggregateReq, _=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, aggregate_reasons, label_catalog_hash
    if req.top < 1 or req.top > 50:
        raise HTTPException(status_code=400, detail="top must be 1..50")
    agg = aggregate_reasons(req.reasons, top=req.top)
    return {
        "catalog_sha": label_catalog_hash(),
        "palette": palette_with_desc(),
        **agg
    }

def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        return datetime.fromisoformat(s.replace("Z","+00:00"))
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

@router.get("/cards/reason-trends/summary")
def get_summary(
    response: Response,
    start: str,
    end: str,
    top: int = 5,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    if_delta_token: Optional[str] = Header(default=None, alias="X-If-Delta-Token"),
    _=Depends(require_scope("ops:read")),
):
    from .cards.aggregation import (
        palette_with_desc, aggregate_reasons, label_catalog_hash,
        make_snapshot_payload, snapshot_etag, snapshot_token, try_decode_token, diff_counts
    )
    from .cards.events import load_reason_events

    if top < 1 or top > 50:
        raise HTTPException(status_code=400, detail="top must be 1..50")
    try:
        dt_start, dt_end = _parse_iso(start), _parse_iso(end)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid start/end")
    if not (dt_end > dt_start):
        raise HTTPException(status_code=400, detail="end must be after start")

    ev_path = os.environ.get("REASON_EVENTS_PATH", "var/evidence/reasons.jsonl")
    reasons = load_reason_events(dt_start, dt_end, ev_path)
    agg = aggregate_reasons(reasons, top=top)
    window = {"start": dt_start.isoformat(), "end": dt_end.isoformat()}
    payload = make_snapshot_payload(window, agg["raw"], label_catalog_hash())
    etag = snapshot_etag(payload)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-cache"

    # 304 처리
    if if_none_match and if_none_match == etag:
        response.status_code = 304
        return None

    # Delta 처리
    delta = None
    if if_delta_token:
        prev = try_decode_token(if_delta_token)
        if prev and isinstance(prev.get("raw"), dict):
            delta = diff_counts(prev["raw"], agg["raw"])

    body = {
        "catalog_sha": payload["catalog_sha"],
        "window": window,
        "palette": palette_with_desc(),
        **agg,
        "delta": delta,
        "delta_token": snapshot_token(payload),
    }
    return body
