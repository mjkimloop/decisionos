from __future__ import annotations

import json
import os
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.common.pii import build_masker


class PIIMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, response_fields: Iterable[str] | None = None) -> None:
        super().__init__(app)
        self.enabled = os.getenv("DECISIONOS_PII_ENABLE", "0") == "1"
        self.response_fields = {f.strip() for f in (response_fields or []) if f.strip()}
        self.masker = build_masker()

    def _redact_payload(self, payload):
        if not self.response_fields:
            return self.masker.mask_event(payload)

        def walk(obj):
            if isinstance(obj, dict):
                return {
                    k: (self.masker.mask_event(v) if k in self.response_fields else walk(v))
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [walk(v) for v in obj]
            if isinstance(obj, str):
                return self.masker.mask_text(obj)
            return obj

        return walk(payload)

    async def _mask_request_body(self, request: Request) -> None:
        """JSON 바디를 마스킹 후 다시 주입한다."""
        try:
            raw = await request.body()
            if not raw:
                return
            data = json.loads(raw.decode("utf-8"))
            masked = self._redact_payload(data)
            new_body = json.dumps(masked).encode("utf-8")
        except Exception:
            return

        async def receive() -> dict:
            return {"type": "http.request", "body": new_body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]

    async def dispatch(self, request, call_next):
        if not self.enabled:
            return await call_next(request)

        await self._mask_request_body(request)
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        if not body:
            return response

        try:
            payload = json.loads(body.decode())
        except Exception:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        masked = self._redact_payload(payload)
        new_body = json.dumps(masked).encode()
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=new_body,
            status_code=response.status_code,
            media_type="application/json",
            headers=headers,
        )
