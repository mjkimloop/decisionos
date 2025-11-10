from __future__ import annotations

from fastapi import Request
from starlette.responses import JSONResponse

from apps.tenancy.loader import get_tenant


def install(app):
    @app.middleware("http")
    async def _tenant_mw(request: Request, call_next):  # type: ignore[override]
        cfg = get_tenant()
        # Enforce header
        tid = request.headers.get("X-Tenant-ID")
        if not tid:
            return JSONResponse({"detail":"X-Tenant-ID required"}, status_code=400)
        if tid != cfg.tenant_id:
            return JSONResponse({"detail":"tenant mismatch"}, status_code=403)
        request.state.tenant = cfg  # attach
        return await call_next(request)

