from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def drift_seconds(now: datetime, reference: datetime) -> float:
    return abs((now - reference).total_seconds())


__all__ = ["now_utc", "drift_seconds"]
