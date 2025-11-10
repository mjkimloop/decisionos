from __future__ import annotations

import uuid
from contextvars import ContextVar

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_trace_hex(trace_hex: str | None) -> None:
    """Store a hexadecimal trace id string."""
    _trace_id.set(trace_hex)


def ensure_trace() -> str:
    """Ensure a trace id is present, generating a pseudo value if needed."""
    val = _trace_id.get()
    if not val:
        val = uuid.uuid4().hex
        _trace_id.set(val)
    return val


def get_trace_id() -> str:
    """Return the active trace id as a hex string."""
    return ensure_trace()
