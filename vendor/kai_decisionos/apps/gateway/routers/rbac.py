from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.rbac import assign_role, revoke_role, list_roles, check_permission, ROLE_PERMISSIONS


router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])


class RoleBody(BaseModel):
    user: str
    role: str


@router.post("/assign")
def assign_ep(body: RoleBody):
    assign_role(body.user, body.role)
    return {"user": body.user, "roles": sorted(list(list_roles(body.user)))}


@router.post("/revoke")
def revoke_ep(body: RoleBody):
    revoke_role(body.user, body.role)
    return {"user": body.user, "roles": sorted(list(list_roles(body.user)))}


@router.get("/user/{user}")
def list_ep(user: str):
    return {"user": user, "roles": sorted(list(list_roles(user)))}


@router.get("/permissions")
def permissions_ep():
    return {k: sorted(list(v)) for k, v in ROLE_PERMISSIONS.items()}


@router.get("/check")
def check_ep(user: str, permission: str):
    return {"user": user, "permission": permission, "allowed": check_permission(user, permission)}

