from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.kyc import SERVICE
from apps.kyc.models import KYCDocument


router = APIRouter(prefix="/api/v1/kyc", tags=["kyc"])


class KYCSubmitBody(BaseModel):
    org_id: str
    type: str
    docs: list[KYCDocument] = Field(default_factory=list)
    risk_tier: str = "low"


@router.post("/submit", status_code=201)
def submit(body: KYCSubmitBody):
    record = SERVICE.submit(org_id=body.org_id, applicant_type=body.type, documents=body.docs, risk_tier=body.risk_tier)
    SERVICE.evaluate(body.org_id)
    return record.model_dump(mode="json")


@router.get("/status")
def status(org_id: str):
    try:
        record = SERVICE.status(org_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="kyc_not_found")
    return record.model_dump(mode="json")
