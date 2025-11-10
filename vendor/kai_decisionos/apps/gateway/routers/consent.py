from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.consent import store as consent_store


router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


class GrantBody(BaseModel):
    subject_id: str
    doc_hash: str
    purpose: str = Field(..., description="Purpose binding identifier")
    scope: list[str] | None = None
    meta: dict | None = None


@router.post("/grant")
def grant_ep(body: GrantBody):
    rec = consent_store.grant(
        body.subject_id,
        body.doc_hash,
        body.purpose,
        scope=body.scope,
        meta=body.meta or {},
    )
    return rec


class RevokeBody(BaseModel):
    subject_id: str
    doc_hash: str
    purpose: str | None = None


@router.post("/revoke")
def revoke_ep(body: RevokeBody):
    rec = consent_store.revoke(body.subject_id, body.doc_hash, purpose=body.purpose)
    if not rec:
        raise HTTPException(404, "not found")
    return rec


@router.get("/list")
def list_ep(subject_id: str, purpose: str | None = None):
    return {"items": consent_store.list_by_subject(subject_id, purpose=purpose)}
