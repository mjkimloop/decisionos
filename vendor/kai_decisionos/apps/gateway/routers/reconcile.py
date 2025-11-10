from __future__ import annotations

from fastapi import APIRouter

from apps.reconcile.matcher import reconcile_charge_event, reconciliation_status


router = APIRouter(prefix="/api/v1/reconcile", tags=["reconcile"])


@router.post("/match")
def reconcile_event(payload: dict):
    result = reconcile_charge_event(payload)
    return result.as_dict()


@router.get("/status")
def status(period: str | None = None):
    return reconciliation_status()


__all__ = ["router"]
