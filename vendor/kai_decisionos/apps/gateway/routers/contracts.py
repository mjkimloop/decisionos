from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.contracts.schema import load_contract
from apps.contracts.validator import validate_payload
from apps.contracts.compat import compare_versions


router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


class ValidateBody(BaseModel):
    contract_path: str
    payload: dict
    kind: str = "input"


@router.post("/validate")
def validate_contract(body: ValidateBody):
    try:
        contract = load_contract(body.contract_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    errors = validate_payload(contract, body.payload, kind=body.kind)
    return {"valid": not errors, "errors": errors}


@router.get("/compare")
def compare(base: str, target: str):
    return compare_versions(base, target)

