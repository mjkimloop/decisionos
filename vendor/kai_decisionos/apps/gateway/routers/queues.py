from __future__ import annotations

from fastapi import APIRouter

from apps.hitl.models import TASKS


router = APIRouter(prefix="/api/v1/queues", tags=["queues"])


@router.get("/{queue_id}/stats")
def queue_stats(queue_id: str):
    total = sum(1 for t in TASKS.values() if t.queue_id == queue_id)
    ready = sum(1 for t in TASKS.values() if t.queue_id == queue_id and t.status == "ready")
    in_prog = sum(1 for t in TASKS.values() if t.queue_id == queue_id and t.status == "in_progress")
    done = sum(1 for t in TASKS.values() if t.queue_id == queue_id and t.status == "done")
    return {"queue_id": queue_id, "total": total, "ready": ready, "in_progress": in_prog, "done": done}

