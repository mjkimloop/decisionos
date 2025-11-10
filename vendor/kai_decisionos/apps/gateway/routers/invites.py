from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.tenancy.invites import create_invite, list_invites, accept_invite


router = APIRouter(prefix="/api/v1/invites", tags=["invites"])


class InviteBody(BaseModel):
    org_id: str
    email: str
    role: str


@router.post("")
def create_ep(body: InviteBody):
    record = create_invite(body.org_id, body.email, body.role)
    return record


@router.get("")
def list_ep(org_id: str | None = None):
    return list_invites(org_id)


class AcceptBody(BaseModel):
    token: str
    user_id: str


@router.post("/accept")
def accept_ep(body: AcceptBody):
    try:
        record = accept_invite(body.token, body.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record

