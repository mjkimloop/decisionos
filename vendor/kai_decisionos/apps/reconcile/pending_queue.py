from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

PENDING: Dict[str, dict] = {}


def add_pending(key: str, payload: dict) -> dict:
    record = {
        **payload,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    PENDING[key] = record
    return record


def resolve_pending(key: str, resolution: str) -> dict | None:
    if key not in PENDING:
        return None
    PENDING[key]["status"] = resolution
    PENDING[key]["resolved_at"] = datetime.now(timezone.utc).isoformat()
    return PENDING[key]


def list_pending() -> List[dict]:
    return list(PENDING.values())


__all__ = ["add_pending", "resolve_pending", "list_pending", "PENDING"]
