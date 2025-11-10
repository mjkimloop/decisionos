from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.tenancy.models import create_org, get_org, ORGS


router = APIRouter(prefix="/api/v1/orgs", tags=["orgs"])


class OrgCreateBody(BaseModel):
    name: str
    plan: str = "free"


@router.post("")
def create_ep(body: OrgCreateBody):
    org = create_org(body.name, body.plan)
    return org.model_dump()


@router.get("/{org_id}")
def get_ep(org_id: str):
    org = get_org(org_id)
    if not org:
        raise HTTPException(404, "not found")
    return org.model_dump()


@router.get("")
def list_ep():
    return [o.model_dump() for o in ORGS.values()]

