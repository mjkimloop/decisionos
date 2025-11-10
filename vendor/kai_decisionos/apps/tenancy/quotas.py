from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ultra-simple sliding window counters (per-day)
_COUNTS_DAY: dict[tuple[str, str, str], list[datetime]] = defaultdict(list)


def add_event(org_id: str, project_id: str | None, metric: str):
    key = (org_id, project_id or "-", metric)
    _COUNTS_DAY[key].append(_utcnow())
    _cleanup()


def count_last_day(org_id: str, project_id: str | None, metric: str) -> int:
    key = (org_id, project_id or "-", metric)
    _cleanup()
    return sum(1 for t in _COUNTS_DAY.get(key, []) if t > _utcnow() - timedelta(days=1))


def _cleanup():
    cutoff = _utcnow() - timedelta(days=1)
    for k, times in list(_COUNTS_DAY.items()):
        _COUNTS_DAY[k] = [t for t in times if t > cutoff]
