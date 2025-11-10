from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter
from starlette.responses import HTMLResponse


router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"]) 


@router.get("/ui")
def hitl_ui():
    base = Path("web/hitl/inbox.html")
    if base.exists():
        return HTMLResponse(base.read_text(encoding="utf-8"))
    return HTMLResponse("<html><body><h1>HITL Inbox</h1></body></html>")

