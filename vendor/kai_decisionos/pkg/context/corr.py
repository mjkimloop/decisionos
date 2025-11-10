from __future__ import annotations

import uuid
from contextvars import ContextVar

_corr_id: ContextVar[str | None] = ContextVar("corr_id", default=None)


def set_corr_id(value: str | None) -> None:
    """Explicitly set the correlation id for the current context."""
    _corr_id.set(value)


def ensure_corr_id() -> str:
    """Ensure a correlation id exists, generating one if needed."""
    val = _corr_id.get()
    if not val:
        val = uuid.uuid4().hex
        _corr_id.set(val)
    return val


def get_corr_id() -> str:
    """Return the correlation id, guaranteeing a value."""
    return ensure_corr_id()
