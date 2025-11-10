from __future__ import annotations

from fastapi import APIRouter

from apps.failover.auto import auto_failover


router = APIRouter(prefix="/api/v1/failover", tags=["failover"]) 


@router.post("/auto")
def failover_auto(force: bool = False):
    return auto_failover(force=force)

