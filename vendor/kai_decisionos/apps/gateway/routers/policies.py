from __future__ import annotations

import re
from dataclasses import asdict
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from apps.policy.store import STORE
from apps.policy.pdp import evaluate

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")


class InstallBody(BaseModel):
    name: str
    bundle: str
    version: str = Field(...)
    approved_by: str
    summary: str | None = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not SEMVER_RE.match(value):
            raise ValueError("invalid_version")
        return value

    @field_validator("approved_by")
    @classmethod
    def validate_approved_by(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("approved_by_required")
        return value


def _install_policy(body: InstallBody):
    try:
        STORE.apply_bundle(
            body.name,
            body.bundle,
            metadata={"version": body.version, "approved_by": body.approved_by, "summary": body.summary},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "applied", "version": body.version, "approved_by": body.approved_by}


@router.post("/install")
def install_policy(body: InstallBody):
    return _install_policy(body)


@router.post("/apply")
def apply_policy(body: InstallBody):
    return _install_policy(body)


class EvalBody(BaseModel):
    subject: dict
    action: str
    resource: dict
    context: dict | None = None


@router.post("/eval")
def eval_policy(body: EvalBody):
    decision = evaluate(body.subject, body.action, body.resource, body.context or {})
    payload = {
        "allow": decision.allow,
        "effect": decision.effect,
        "policy_id": decision.policy_id,
        "reason": decision.reason,
        "purpose": decision.purpose,
        "bundle": decision.bundle,
        "trace": [asdict(trace) for trace in decision.trace],
    }
    return payload


@router.get("/list")
def list_policies():
    response: dict = {}
    for name, bundle in STORE.list_policies().items():
        response[name] = {
            "metadata": bundle.metadata.__dict__ if bundle.metadata else None,
            "policies": [p.__dict__ for p in bundle.policies],
        }
    return response
