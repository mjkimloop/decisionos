from __future__ import annotations
from datetime import datetime, timezone

from .clock import now_utc

def time_utcnow() -> datetime:
    return now_utc()

def within_clock_skew(now: datetime, ts: datetime, skew_sec: int = 90) -> bool:
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware(UTC)")
    delta = abs((now - ts).total_seconds())
    return delta <= skew_sec
