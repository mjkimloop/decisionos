from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    company: str
    plan: str = Field(default="trial")
    notes: Optional[str] = None


class SignupRecord(SignupRequest):
    id: str
    created_at: datetime


class BootstrapRequest(BaseModel):
    signup_id: str
    org_name: str
    project_name: str
    region: str = Field(default="region-a")


class BootstrapResult(BaseModel):
    org_id: str
    project_id: str
    api_key: str


__all__ = [
    "SignupRequest",
    "SignupRecord",
    "BootstrapRequest",
    "BootstrapResult",
]
