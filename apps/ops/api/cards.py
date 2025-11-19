from __future__ import annotations

import os
import time
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from apps.ops.cache.etag_store import ETagStore, get_store
from apps.ops.api.cards_data import aggregate as aggregate_from_evidence
from apps.ops.schemas import CardsReasonTrendsResponse, CardsDeltaResponse
from apps.policy.rbac_enforce import require_scopes
from apps.common.pydantic_compat import model_to_dict

router = APIRouter(prefix="/ops/cards")
_STORE: ETagStore = get_store()


def _build_reason_trends(period: str, bucket: str) -> Dict[str, Any]:
    # Evidence 인덱스/카탈로그 기반 집계
    return aggregate_from_evidence(period, bucket)


def _delta(prev: Dict[str, Any], cur: Dict[str, Any]) -> Dict[str, Any]:
    dp, dc = prev.get("groups", {}), cur.get("groups", {})
    out = {"period": cur.get("period"), "bucket": cur.get("bucket"), "delta": True, "groups": {}}
    keys = set(dp.keys()) | set(dc.keys())
    for k in keys:
        pv = dp.get(k, {"count": 0, "weight": 0})
        cv = dc.get(k, {"count": 0, "weight": 0})
        out["groups"][k] = {
            "d_count": cv.get("count", 0) - pv.get("count", 0),
            "d_score": (cv.get("count", 0) * cv.get("weight", 0)) - (pv.get("count", 0) * pv.get("weight", 0)),
        }
    out["generated_at"] = cur.get("generated_at")
    out["top"] = cur.get("top", [])
    return out


@router.get(
    "/reason-trends",
    response_model=Union[CardsReasonTrendsResponse, CardsDeltaResponse],
    dependencies=[require_scopes("ops:read")]
)
def reason_trends(request: Request, response: Response, period: str = "7d", bucket: str = "day"):
    key = f"cards:reason-trends:{period}:{bucket}"
    payload = _build_reason_trends(period, bucket)
    etag = _STORE.compute_etag(payload, extra=key)

    inm = request.headers.get("if-none-match")
    if inm and inm == etag:
        response.status_code = 304
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "private, max-age=60"
        response.headers["Vary"] = "Accept-Encoding, X-Scopes"
        return

    delta_base = request.headers.get("x-delta-base-etag") or request.headers.get("X-Delta-Base-ETag")
    body = payload
    is_delta = False
    if delta_base:
        prev = _STORE.get(key)
        if prev and prev[0] == delta_base:
            body = _delta(prev[1], payload)
            is_delta = True
            response.headers["X-Delta-Base-ETag"] = delta_base
            response.headers["X-Delta-Mode"] = "1"

    _STORE.set(key, etag, payload, ttl_sec=int(os.getenv("DECISIONOS_CARDS_TTL", "60")))
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["Vary"] = "Accept-Encoding, X-Scopes"
    response.headers["Last-Modified"] = str(payload.get("generated_at", int(time.time())))

    # Wrap in schema models for validation
    if is_delta:
        # Delta response has different structure
        return body  # CardsDeltaResponse will be inferred
    else:
        # Full response
        validated = CardsReasonTrendsResponse(**payload)
        return model_to_dict(validated)
