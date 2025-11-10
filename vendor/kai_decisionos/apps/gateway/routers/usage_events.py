from __future__ import annotations

import json
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from packages.common.config import settings
from apps.security.hmac import verify_hmac_sha256
from apps.meter.collector import ingest_event

_seen_ids: set[str] = set()

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.post("/events")
async def post_usage_event(request: Request):
    body = await request.body()
    idem = request.headers.get("Idempotency-Key")
    sig = request.headers.get("X-Signature")
    if settings.usage_hmac_secret:
        if not sig or not verify_hmac_sha256(settings.usage_hmac_secret, body, sig):
            return JSONResponse({"detail": "invalid signature"}, status_code=401)
    if idem:
        if idem in _seen_ids:
            return JSONResponse({"status": "duplicate"}, status_code=200)
        _seen_ids.add(idem)
    try:
        data = json.loads(body.decode("utf-8"))
        # minimal: expect org_id,event,value
        org_id = data.get("org_id")
        event = data.get("event") or data.get("metric")
        value = data.get("value", 1)
        ingest_event({"org_id": org_id, "metric": event, "value": value})
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=400)
