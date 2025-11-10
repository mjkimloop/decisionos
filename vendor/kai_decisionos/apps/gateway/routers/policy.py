from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.policy.validator import validate_policy
from apps.policy.simulator import simulate
from apps.policy.enforce import enforce


router = APIRouter(prefix="/api/v1/policy", tags=["policy"]) 


class ValidateBody(BaseModel):
    policy: dict


@router.post("/validate")
def validate_ep(body: ValidateBody):
    res = validate_policy(body.policy)
    return res


class SimBody(BaseModel):
    policy: dict
    rows: list[dict]


@router.post("/simulate")
def simulate_ep(body: SimBody):
    return simulate(body.policy, body.rows)


class EnforceBody(BaseModel):
    stage: str
    policy: dict
    payload: dict


@router.post("/enforce")
def enforce_ep(body: EnforceBody):
    return enforce(body.stage, body.policy, body.payload)

