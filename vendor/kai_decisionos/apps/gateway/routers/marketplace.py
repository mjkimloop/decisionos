from __future__ import annotations

from fastapi import APIRouter

from apps.ext.registry.oci import REGISTRY

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


@router.get("/list")
def list_marketplace(channel: str = "private-beta"):
    artifacts = REGISTRY.list_channel(channel)
    return [artifact.__dict__ for artifact in artifacts]


__all__ = ["router"]
