from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Org(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    plan: str = "free"
    status: str = "active"
    created_at: datetime = Field(default_factory=_utcnow)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    name: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


ORGS: dict[str, Org] = {}
PROJECTS: dict[str, Project] = {}


def create_org(name: str, plan: str = "free") -> Org:
    org = Org(name=name, plan=plan)
    ORGS[org.id] = org
    return org


def get_org(org_id: str) -> Optional[Org]:
    return ORGS.get(org_id)


def create_project(org_id: str, name: str) -> Project:
    prj = Project(org_id=org_id, name=name)
    PROJECTS[prj.id] = prj
    return prj
