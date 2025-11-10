from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.tenancy.pat import create_token, list_tokens, revoke_token


router = APIRouter(prefix="/api/v1/pat", tags=["pat"])


class PATBody(BaseModel):
    user_id: str
    label: str = "cli"


@router.post("")
def create_pat(body: PATBody):
    record = create_token(body.user_id, body.label)
    return record


@router.get("")
def list_pat(user_id: str):
    return list_tokens(user_id)


@router.post("/revoke")
def revoke_pat(token: str):
    revoke_token(token)
    return {"token": token, "revoked": True}

