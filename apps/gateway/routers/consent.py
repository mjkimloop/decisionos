from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from apps.consent.store import ConsentRecord, get_store
from apps.policy.rbac_enforce import require_scopes

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])
store = get_store()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SCOPE_PATTERN = r"^[a-z0-9:_-]+(,[a-z0-9:_-]+)*$"


class GrantRequest(BaseModel):
    subject_id: str = Field(min_length=1)
    doc_hash: str = Field(min_length=8)
    scope: str = Field(pattern=SCOPE_PATTERN)
    ttl_sec: int = Field(ge=60)


class RevokeRequest(BaseModel):
    subject_id: str = Field(min_length=1)
    doc_hash: str = Field(min_length=8)


class ConsentResponse(BaseModel):
    subject_id: str
    doc_hash: str
    scope: str
    granted_at: str
    ttl_sec: int
    revoked: bool
    version: str
    prev_hash: str
    curr_hash: str

    @classmethod
    def from_record(cls, rec: ConsentRecord) -> "ConsentResponse":
        return cls(**rec.__dict__)


@router.post("/grant", dependencies=[require_scopes("consent:write")], response_model=ConsentResponse, status_code=201)
async def grant(body: GrantRequest):
    rec = ConsentRecord(
        subject_id=body.subject_id,
        doc_hash=body.doc_hash,
        scope=body.scope,
        ttl_sec=body.ttl_sec,
        granted_at=_utcnow_iso(),
    )
    rec = await store.grant(rec)
    return ConsentResponse.from_record(rec)


@router.post("/revoke", dependencies=[require_scopes("consent:write")], status_code=204)
async def revoke(body: RevokeRequest):
    try:
        await store.revoke(body.subject_id, body.doc_hash)
    except LookupError:
        raise HTTPException(status_code=404, detail="not found")
    return {}


@router.get("/{subject_id}", dependencies=[require_scopes("consent:read")], response_model=List[ConsentResponse])
async def list_consent(subject_id: str):
    recs = await store.list(subject_id)
    return [ConsentResponse.from_record(r) for r in recs]
