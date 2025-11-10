from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.hitl.models import submit_appeal, resolve_appeal, APPEALS


router = APIRouter(prefix="/api/v1/appeals", tags=["appeals"])


class SubmitBody(BaseModel):
    case_id: str
    reason: str | None = None
    attachments: list[dict] | None = None
    submitted_by: str | None = None
    level: int = 1


@router.post("/submit")
def submit_ep(body: SubmitBody):
    a = submit_appeal(body.case_id, body.submitted_by, body.level)
    return a.model_dump()


@router.get("/{appeal_id}")
def get_ep(appeal_id: str):
    a = APPEALS.get(appeal_id)
    if not a:
        raise HTTPException(404, "not found")
    return a.model_dump()


class ResolveBody(BaseModel):
    resolution: str
    message: str | None = None


@router.post("/{appeal_id}/resolve")
def resolve_ep(appeal_id: str, body: ResolveBody):
    a = resolve_appeal(appeal_id, body.resolution)
    if not a:
        raise HTTPException(404, "not found")
    return a.model_dump()

