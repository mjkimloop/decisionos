from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from base64 import urlsafe_b64encode, urlsafe_b64decode
import os, json

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

def _encode_cont_token(bucket_size: str, last_end_iso: str) -> str:
    obj = {"bucket_size": bucket_size, "last_end": last_end_iso}
    return urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode("utf-8")).decode("ascii")

def _decode_cont_token(token: str) -> dict | None:
    try:
        obj = json.loads(urlsafe_b64decode(token.encode("ascii")).decode("utf-8"))
        if not isinstance(obj, dict):
            return None
        return obj
    except Exception:
        return None

@router.get("/cards/reason-trends/summary")
def get_summary(
    response: Response,
    start: str,
    end: str,
    top: int = 5,
    bucket: Optional[str] = None,
    bucket_limit: int = 24,
    top_buckets: int = 3,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    if_delta_token: Optional[str] = Header(default=None, alias="X-If-Delta-Token"),
    cont_token: Optional[str] = Header(default=None, alias="X-Bucket-Continuity-Token"),
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

    # 버킷 분포 (+ 연속 토큰 페이지네이션)
    buckets = None
    buckets_scored = None
    top_list = None
    cont_out = None
    has_more = False

    if bucket:
        from .cards.bucketing import bucketize_counts_by_time, apply_bucket_scores, pick_top_buckets
        from .cards.grouping import group_of, load_group_weights

        if bucket not in ("hour", "day"):
            raise HTTPException(status_code=400, detail="bucket must be 'hour' or 'day'")
        if bucket_limit < 1 or bucket_limit > 1000:
            raise HTTPException(status_code=400, detail="bucket_limit must be 1..1000")

        # Load rows with ts + reason
        rows = []
        from .cards.events import load_reason_events
        ev_path2 = os.environ.get("REASON_EVENTS_PATH", "var/evidence/reasons.jsonl")
        if os.path.exists(ev_path2):
            with open(ev_path2, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    ts_str = obj.get("ts", "")
                    reason = obj.get("reason", "")
                    if ts_str and reason:
                        # Parse and filter by window
                        try:
                            ts = _parse_iso(ts_str)
                            if ts >= dt_start and ts < dt_end:
                                rows.append({"ts": ts_str, "reason": reason})
                        except Exception:
                            pass

        all_buckets = bucketize_counts_by_time(rows, bucket)

        # continuity offset
        offset_idx = 0
        if cont_token:
            prev = _decode_cont_token(cont_token)
            if prev and prev.get("bucket_size") == bucket and "last_end" in prev:
                last_end = _parse_iso(prev["last_end"])
                # 현재 윈도 내에서 last_end 이후 버킷부터
                for i, b in enumerate(all_buckets):
                    if _parse_iso(b["end"]) > last_end:
                        offset_idx = i
                        break
                else:
                    offset_idx = len(all_buckets)

        page = all_buckets[offset_idx:offset_idx + bucket_limit]
        buckets = page

        # 다음 페이지 토큰
        has_more = (offset_idx + bucket_limit) < len(all_buckets)
        if page:
            last_end_iso = page[-1]["end"]
            cont_out = _encode_cont_token(bucket, last_end_iso)
            response.headers["X-Bucket-Continuity-Token"] = cont_out
        response.headers["X-Bucket-Has-More"] = "1" if has_more else "0"

        # 가중 점수 & 상위 N 버킷
        if buckets:
            weights = load_group_weights()
            buckets_scored = apply_bucket_scores(buckets, group_of, weights)
            if top_buckets and top_buckets > 0:
                top_list = pick_top_buckets(buckets_scored, top_buckets)

    body = {
        "catalog_sha": payload["catalog_sha"],
        "window": window,
        "palette": palette_with_desc(),
        **agg,
        "buckets": buckets_scored if buckets_scored is not None else buckets,
        "top_buckets": top_list,
        "delta": delta,
        "delta_token": snapshot_token(payload),
        "continuity": {
            "bucket_size": bucket,
            "token": cont_out,
            "has_more": has_more,
            "limit": bucket_limit,
        } if bucket else None,
    }
    return body
