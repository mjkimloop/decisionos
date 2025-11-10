from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.tenancy.entitlements import (
    check_entitlement,
    grant_entitlement,
    revoke_entitlement,
    list_effective_entitlements,
)


router = APIRouter(prefix="/api/v1/entitlements", tags=["entitlements"])


class CheckBody(BaseModel):
    org_id: str
    feature: str


@router.post("/check")
def check_ep(body: CheckBody):
    ok = check_entitlement(body.org_id, body.feature)
    return {"ok": ok}


class GrantBody(BaseModel):
    org_id: str
    feature: str


@router.post("/grant")
def grant_ep(body: GrantBody):
    grant_entitlement(body.org_id, body.feature)
    return {"granted": body.feature}


@router.post("/revoke")
def revoke_ep(body: GrantBody):
    revoke_entitlement(body.org_id, body.feature)
    return {"revoked": body.feature}


@router.get("/org/{org_id}")
def list_ep(org_id: str):
    ents = list_effective_entitlements(org_id)
    return {"org_id": org_id, "entitlements": sorted(ents)}
