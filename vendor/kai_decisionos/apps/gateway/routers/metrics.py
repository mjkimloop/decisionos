from __future__ import annotations

from fastapi import APIRouter

from apps.gateway.middleware import metrics as metrics_mw


router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("")
def metrics_ep():
    snap = metrics_mw.snapshot()
    return {"metrics": snap}


@router.get("/healthz")
def healthz():
    return {"ok": True}
