from __future__ import annotations

from fastapi import Request
from starlette.responses import Response

from pkg.context.corr import ensure_corr_id, set_corr_id, get_corr_id


def install(app):
    @app.middleware("http")
    async def _corr_mw(request: Request, call_next):  # type: ignore[override]
        incoming = request.headers.get("X-Corr-Id") or request.headers.get("X-Correlation-Id")
        if incoming:
            set_corr_id(incoming)
        request.state.corr_id = ensure_corr_id()
        response: Response = await call_next(request)
        response.headers["X-Corr-Id"] = request.state.corr_id
        return response
