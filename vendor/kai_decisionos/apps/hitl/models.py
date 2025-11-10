from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional, Literal, Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Case(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    project_id: Optional[str] = None
    decision_id: Optional[str] = None
    status: Literal["open", "pending", "awaiting_docs", "escalated", "closed"] = "open"
    priority: Literal["p0", "p1", "p2", "p3"] = "p2"
    reason_codes: list[str] = Field(default_factory=list)
    sla_due_at: Optional[datetime] = None
    owner_user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    kind: Literal["review", "qa", "request_docs", "call", "verify"] = "review"
    status: Literal["ready", "in_progress", "blocked", "done"] = "ready"
    assignee_user_id: Optional[str] = None
    queue_id: Optional[str] = None
    due_at: Optional[datetime] = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Appeal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    level: int = 1
    status: Literal["submitted", "in_review", "resolved", "rejected"] = "submitted"
    submitted_by: Optional[str] = None
    resolution: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# In-memory stores (dev only)
CASES: dict[str, Case] = {}
TASKS: dict[str, Task] = {}
APPEALS: dict[str, Appeal] = {}


DEFAULT_SLA_HOURS = {"p0": 4, "p1": 24, "p2": 48, "p3": 72}


def open_case(org_id: str, project_id: Optional[str], decision_id: Optional[str], priority: str,
              context: Optional[dict] = None) -> Case:
    pr = priority if priority in DEFAULT_SLA_HOURS else "p2"
    case = Case(org_id=org_id, project_id=project_id, decision_id=decision_id, priority=pr)
    hours = DEFAULT_SLA_HOURS[case.priority]
    case.sla_due_at = _utcnow() + timedelta(hours=hours)
    CASES[case.id] = case
    # create initial review task
    task = Task(case_id=case.id, kind="review", queue_id=f"q:{case.priority}")
    TASKS[task.id] = task
    return case


def get_case(case_id: str) -> Optional[Case]:
    return CASES.get(case_id)


def update_case(case_id: str, **updates) -> Optional[Case]:
    c = CASES.get(case_id)
    if not c:
        return None
    for k, v in updates.items():
        if hasattr(c, k) and v is not None:
            setattr(c, k, v)
    c.updated_at = _utcnow()
    CASES[c.id] = c
    return c


def pop_next_task(queue_id: Optional[str] = None) -> Optional[Task]:
    # naive: pick first ready in queue or any
    for t in TASKS.values():
        if t.status == "ready" and (queue_id is None or t.queue_id == queue_id):
            t.status = "in_progress"
            t.updated_at = _utcnow()
            return t
    return None


def complete_task(task_id: str, action: str, payload: Optional[dict] = None) -> Optional[Task]:
    t = TASKS.get(task_id)
    if not t:
        return None
    t.status = "done"
    t.payload_json = payload or {}
    t.updated_at = _utcnow()
    TASKS[t.id] = t
    # reflect basic actions to case
    c = CASES.get(t.case_id)
    if c:
        if action == "approve":
            c.status = "closed"
        elif action == "deny":
            c.status = "closed"
        elif action == "request_docs":
            c.status = "awaiting_docs"
        elif action == "escalate":
            c.status = "escalated"
        c.updated_at = _utcnow()
        CASES[c.id] = c
    return t


def submit_appeal(case_id: str, submitted_by: Optional[str], level: int = 1) -> Appeal:
    a = Appeal(case_id=case_id, submitted_by=submitted_by, level=level)
    APPEALS[a.id] = a
    # create review task for senior queue
    t = Task(case_id=case_id, kind="review", queue_id=f"senior:{level}")
    TASKS[t.id] = t
    return a


def resolve_appeal(appeal_id: str, resolution: str) -> Optional[Appeal]:
    a = APPEALS.get(appeal_id)
    if not a:
        return None
    a.status = "resolved"
    a.resolution = resolution
    a.updated_at = _utcnow()
    APPEALS[a.id] = a
    return a
