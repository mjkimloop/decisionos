from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from apps.backlog.models import BacklogSubmit
from apps.backlog.store import add_item, list_items


router = APIRouter(prefix="/api/v1/backlog", tags=["backlog"])


@router.post("/items", status_code=201)
def create_item(payload: BacklogSubmit):
    item = add_item(payload)
    return item.model_dump(mode="json")


@router.get("/items")
def backlog_items():
    items = sorted(list_items(), key=lambda x: x.rice, reverse=True)
    return {"items": [item.model_dump(mode="json") for item in items]}

