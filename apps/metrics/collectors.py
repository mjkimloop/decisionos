from __future__ import annotations

import time
from typing import Callable

from fastapi import FastAPI, Request, Response

from apps.metrics.registry import METRICS


def add_latency_middleware(app: FastAPI):
    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next: Callable):
        start = time.time()
        resp: Response
        try:
            resp = await call_next(request)
            status = resp.status_code
        except Exception:
            status = 500
            raise
        finally:
            dur_ms = (time.time() - start) * 1000
            METRICS.observe("http_latency_ms", {"path": request.url.path}, dur_ms)
            if status >= 500:
                METRICS.inc("http_errors_total", {"path": request.url.path})
            METRICS.inc("http_requests_total", {"path": request.url.path})
        return resp

