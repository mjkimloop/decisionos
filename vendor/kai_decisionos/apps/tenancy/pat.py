from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Dict, List


PERSONAL_TOKENS: Dict[str, dict] = {}


def create_token(user_id: str, label: str = "cli") -> dict:
    token = secrets.token_urlsafe(24)
    record = {
        "token": token,
        "user_id": user_id,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "revoked": False,
    }
    PERSONAL_TOKENS[token] = record
    return record


def list_tokens(user_id: str) -> List[dict]:
    return [token for token in PERSONAL_TOKENS.values() if token["user_id"] == user_id]


def revoke_token(token: str) -> None:
    rec = PERSONAL_TOKENS.get(token)
    if rec:
        rec["revoked"] = True


__all__ = ["PERSONAL_TOKENS", "create_token", "list_tokens", "revoke_token"]

