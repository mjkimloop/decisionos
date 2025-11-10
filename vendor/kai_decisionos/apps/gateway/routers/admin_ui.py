from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse


router = APIRouter(prefix="/admin", tags=["admin-ui"])


@router.get("/console", response_class=HTMLResponse)
def admin_console():
    path = Path(__file__).resolve().parents[3] / "web" / "admin" / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="admin ui not found")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))

