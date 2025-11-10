from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import secrets


@dataclass
class Session:
    session_id: str
    subject: str
    issued_at: datetime
    expires_at: datetime


_SESSIONS: Dict[str, Session] = {}


def create_session(subject: str, ttl_minutes: int = 60) -> Session:
    session_id = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    sess = Session(session_id=session_id, subject=subject, issued_at=now, expires_at=now + timedelta(minutes=ttl_minutes))
    _SESSIONS[session_id] = sess
    return sess


def get_session(session_id: str) -> Optional[Session]:
    sess = _SESSIONS.get(session_id)
    if not sess:
        return None
    if sess.expires_at < datetime.now(timezone.utc):
        _SESSIONS.pop(session_id, None)
        return None
    return sess


def invalidate_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


__all__ = ["Session", "create_session", "get_session", "invalidate_session"]

