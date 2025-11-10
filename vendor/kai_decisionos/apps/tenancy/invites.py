from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional


INVITES: Dict[str, dict] = {}


def create_invite(org_id: str, email: str, role: str) -> dict:
    token = secrets.token_urlsafe(16)
    record = {
        "token": token,
        "org_id": org_id,
        "email": email,
        "role": role,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "accepted_at": None,
    }
    INVITES[token] = record
    return record


def list_invites(org_id: str | None = None) -> List[dict]:
    items = list(INVITES.values())
    if org_id:
        items = [i for i in items if i["org_id"] == org_id]
    return items


def accept_invite(token: str, user_id: str) -> dict:
    record = INVITES.get(token)
    if not record:
        raise KeyError("invite_not_found")
    record["status"] = "accepted"
    record["accepted_at"] = datetime.now(timezone.utc).isoformat()
    record["accepted_by"] = user_id
    return record


__all__ = ["INVITES", "create_invite", "list_invites", "accept_invite"]

