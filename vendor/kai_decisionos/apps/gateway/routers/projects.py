from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.tenancy.models import create_project, PROJECTS, ORGS


router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreateBody(BaseModel):
    org_id: str
    name: str


@router.post("")
def create_ep(body: ProjectCreateBody):
    if body.org_id not in ORGS:
        raise HTTPException(400, "invalid org_id")
    prj = create_project(body.org_id, body.name)
    return prj.model_dump()


@router.get("")
def list_ep(org_id: str | None = None):
    items = list(PROJECTS.values())
    if org_id:
        items = [p for p in items if p.org_id == org_id]
    return [p.model_dump() for p in items]

