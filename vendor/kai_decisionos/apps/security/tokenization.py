from __future__ import annotations

import secrets
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_PREFIX = "tok_"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TokenEntry:
    value: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        return bool(self.expires_at and _now() > self.expires_at)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = payload["created_at"].isoformat()
        payload["expires_at"] = payload["expires_at"].isoformat() if payload["expires_at"] else None
        return payload


_TOKENS: Dict[str, TokenEntry] = {}


def tokenize(value: str, *, metadata: Optional[Dict[str, Any]] = None, ttl_seconds: Optional[int] = None) -> str:
    """Create a reversible token with optional metadata and TTL."""
    if not isinstance(value, str):
        raise TypeError("value must be str")
    entry = TokenEntry(
        value=value,
        metadata=dict(metadata or {}),
        expires_at=(_now() + timedelta(seconds=ttl_seconds)) if ttl_seconds else None,
    )
    with _LOCK:
        token = _PREFIX + secrets.token_urlsafe(16)
        _TOKENS[token] = entry
        return token


def detokenize(token: str, *, expected_metadata: Optional[Dict[str, Any]] = None) -> str:
    with _LOCK:
        entry = _TOKENS.get(token)
        if entry is None or entry.is_expired():
            raise KeyError("unknown_token")
        if expected_metadata:
            for key, value in expected_metadata.items():
                if entry.metadata.get(key) != value:
                    raise PermissionError("token_scope_mismatch")
        return entry.value


def inspect(token: str) -> Dict[str, Any]:
    with _LOCK:
        entry = _TOKENS[token]
        return entry.to_dict()


def clear_tokens() -> None:
    with _LOCK:
        _TOKENS.clear()


__all__ = ["tokenize", "detokenize", "inspect", "clear_tokens", "TokenEntry"]
