from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from apps.onboarding.models import SignupRequest, BootstrapRequest
from apps.onboarding.service import (
    register_signup,
    list_signups,
    bootstrap_tenant,
)


router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For")):
    record = register_signup(payload)
    return {"id": record.id, "email": record.email, "plan": record.plan, "source": x_forwarded_for}


@router.get("/signups")
def signups():
    return {"items": [record.model_dump(mode="json") for record in list_signups()]}


@router.post("/bootstrap")
def bootstrap(payload: BootstrapRequest):
    # Basic validation: ensure signup exists
    if payload.signup_id not in {s.id for s in list_signups()}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signup not found")
    result = bootstrap_tenant(payload)
    return result.model_dump(mode="json")

