from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.vault.service import set_secret, get_secret


router = APIRouter(prefix="/api/v1/vault", tags=["vault"]) 


class SetBody(BaseModel):
    key: str
    value: str


@router.post("/set")
def set_ep(body: SetBody):
    set_secret(body.key, body.value)
    return {"ok": True}


@router.get("/get")
def get_ep(key: str):
    val = get_secret(key)
    if val is None:
        raise HTTPException(404, "not found")
    return {"key": key, "value": val}

