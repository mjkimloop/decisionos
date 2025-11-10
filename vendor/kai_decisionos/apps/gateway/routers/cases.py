from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.hitl.models import open_case, get_case, update_case


router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class OpenCaseBody(BaseModel):
    org_id: str
    project_id: Optional[str] = None
    decision_id: Optional[str] = None
    priority: str = "p2"
    context: Optional[dict] = None


@router.post("/open")
def open_case_ep(body: OpenCaseBody):
    case = open_case(body.org_id, body.project_id, body.decision_id, body.priority, body.context)
    return case.model_dump()


@router.get("/{case_id}")
def get_case_ep(case_id: str):
    c = get_case(case_id)
    if not c:
        raise HTTPException(404, "not found")
    return c.model_dump()


class PatchCaseBody(BaseModel):
    status: Optional[str] = None
    owner_user_id: Optional[str] = None
    priority: Optional[str] = None


@router.patch("/{case_id}")
def patch_case_ep(case_id: str, body: PatchCaseBody):
    c = update_case(case_id, **{k: v for k, v in body.model_dump().items() if v is not None})
    if not c:
        raise HTTPException(404, "not found")
    return c.model_dump()

