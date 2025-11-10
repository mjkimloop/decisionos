from __future__ import annotations

from fastapi import APIRouter, Depends
from packages.schemas.api import SimulateResponse
from apps.executor.pipeline import simulate as do_simulate
from apps.executor.exceptions import DomainError

router = APIRouter()


def auth_dep():
    return None


@router.post("/api/v1/simulate/{contract}", response_model=SimulateResponse)
def simulate(contract: str, payload: dict, _: None = Depends(auth_dep)):
    rows = payload.get("rows") or []
    label_key = payload.get("label_key")
    try:
        metrics = do_simulate(contract, rows=rows, label_key=label_key)
    except DomainError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=e.status_code, detail=e.message)
    return metrics
