from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.hitl.models import pop_next_task, complete_task


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class NextBody(BaseModel):
    queue_id: Optional[str] = None


@router.post("/next")
def next_task_ep(body: NextBody):
    t = pop_next_task(body.queue_id)
    if not t:
        return {"task": None}
    return {"task": t.model_dump()}


class ActionBody(BaseModel):
    action: str
    payload: Optional[dict] = None


@router.post("/{task_id}/action")
def task_action_ep(task_id: str, body: ActionBody):
    t = complete_task(task_id, body.action, body.payload)
    if not t:
        raise HTTPException(404, "not found")
    return {"ok": True, "task": t.model_dump()}

