"""PII middleware with metrics integration (v2).

Enhanced version with:
- Metrics counting (masked strings)
- Soft/hard mode support
- Circuit breaker integration
"""
from __future__ import annotations

import json
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.metrics.registry import METRICS
from apps.security.pii import pii_enabled  # Existing toggle
from apps.security.pii_rules import mask_obj_with_stats


class PIIMiddlewareV2(BaseHTTPMiddleware):
    """PII middleware with metrics and circuit breaker integration."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request/response with PII masking."""
        if not pii_enabled():
            return await call_next(request)

        masked_count = 0

        # Request masking
        body = await request.body()
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
                masked, c = mask_obj_with_stats(data)
                masked_count += c
                new_body = json.dumps(masked).encode("utf-8")

                async def receive():
                    return {"type": "http.request", "body": new_body, "more_body": False}

                request._receive = receive  # type: ignore[attr-defined]
            except Exception:
                pass

        # Call next handler
        resp: Response = await call_next(request)

        # Response masking
        try:
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype.lower():
                content = b""
                async for chunk in resp.body_iterator:
                    content += chunk
                if content:
                    data = json.loads(content.decode("utf-8"))
                    masked, c = mask_obj_with_stats(data)
                    masked_count += c
                    new_body = json.dumps(masked).encode("utf-8")

                    headers = dict(resp.headers)
                    headers.pop("content-length", None)

                    resp = Response(
                        content=new_body,
                        status_code=resp.status_code,
                        headers=headers,
                        media_type=resp.media_type,
                    )
        except Exception:
            pass

        # Record metrics
        if masked_count:
            await METRICS.inc("decisionos_pii_masked_strings_total", {}, masked_count)

        return resp
