from __future__ import annotations

import email.utils
import hashlib
import json
import os
import time
from typing import Any, Dict

from fastapi import APIRouter, Request, Response

from apps.ops.api.cards_data import compute_reason_trends
from apps.ops.cache.snapshot_store import SnapshotStore
from apps.policy.rbac_enforce import require_scopes

# Optional metrics
try:
    from apps.metrics.registry import METRICS_V2 as METRICS
except Exception:
    METRICS = None

TENANT = os.getenv("DECISIONOS_TENANT", "").strip()
CATALOG_SHA = os.getenv("DECISIONOS_LABEL_CATALOG_SHA", "").strip()
_TTL = int(os.getenv("DECISIONOS_CARDS_TTL", "60"))
_SNAP = SnapshotStore()

router = APIRouter(
    prefix="/ops/cards",
    tags=["ops-cards"],
    dependencies=[require_scopes("ops:read")],
)


def _cache_key(q: Dict[str, Any]) -> str:
    """Prevent key collision by folding tenant/catalog/q into the key."""
    qhash = hashlib.sha1(json.dumps(q, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    parts = [p for p in (TENANT, "cards:reason-trends", CATALOG_SHA, qhash) if p]
    return ":".join(parts)


def _etag(body: dict, q: Dict[str, Any]) -> str:
    raw = json.dumps({"t": TENANT, "c": CATALOG_SHA, "body": body.get("generated_at"), "q": q}, sort_keys=True, separators=(",", ":")).encode()
    return '"' + hashlib.sha256(raw).hexdigest() + '"'


def _httpdate(ts: float) -> str:
    return email.utils.formatdate(ts, usegmt=True)


@router.get("/reason-trends")
async def reason_trends(request: Request, period: str = "7d", bucket: str = "day"):
    q = {"period": period, "bucket": bucket}
    body_obj = compute_reason_trends(period=period, bucket=bucket)
    body_json = json.dumps(body_obj, ensure_ascii=False)
    etag = _etag(body_obj, q)

    if request.headers.get("If-None-Match") == etag:
        resp = Response(status_code=304)
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = f"private, max-age={_TTL}"
        resp.headers["Vary"] = "Authorization, X-Scopes, X-Tenant, Accept, If-None-Match, If-Modified-Since"
        resp.headers["Content-Length"] = "0"
        return resp

    snap_key = _cache_key(q)
    prev = _SNAP.get(snap_key)
    delta = None
    if prev:
        try:
            prev_obj = json.loads(prev[0])
            prev_top = {x["reason"]: x["score"] for x in prev_obj.get("top_reasons", [])}
            curr_top = {x["reason"]: x["score"] for x in body_obj.get("top_reasons", [])}
            added = {k: curr_top[k] for k in curr_top.keys() - prev_top.keys()}
            removed = {k: prev_top[k] for k in prev_top.keys() - curr_top.keys()}
            changed = {
                k: curr_top[k] - prev_top.get(k, 0)
                for k in curr_top.keys() & prev_top.keys()
                if abs(curr_top[k] - prev_top[k]) > 1e-6
            }
            delta = {"added": added, "removed": removed, "changed": changed}
        except Exception:
            delta = None

    payload = {"data": body_obj, "delta": delta, "_meta": {"tenant": TENANT, "catalog_sha": CATALOG_SHA}}
    resp = Response(content=json.dumps(payload, ensure_ascii=False), media_type="application/json")
    resp.headers["ETag"] = etag
    resp.headers["Last-Modified"] = _httpdate(time.time())
    resp.headers["Cache-Control"] = f"private, max-age={_TTL}"
    resp.headers["Vary"] = "Authorization, X-Scopes, X-Tenant, Accept, If-None-Match, If-Modified-Since"
    _SNAP.set(snap_key, body_json)
    if METRICS:
        await METRICS.inc("decisionos_cards_etag_total", {"result": "miss"})
    return resp
