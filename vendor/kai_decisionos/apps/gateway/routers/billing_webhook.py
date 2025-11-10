from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from packages.common.config import settings
from apps.security.hmac import verify_hmac_sha256

_last_event: dict | None = None

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.post("/webhook")
async def webhook(request: Request):
    global _last_event
    body = await request.body()
    sig = request.headers.get("X-Signature")
    if settings.billing_webhook_secret:
        if not sig or not verify_hmac_sha256(settings.billing_webhook_secret, body, sig):
            return JSONResponse({"detail": "invalid signature"}, status_code=401)
    try:
        _last_event = await request.json()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=400)


@router.get("/webhook/last")
def webhook_last():
    return {"event": _last_event}
