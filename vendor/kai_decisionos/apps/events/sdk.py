from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_EVENT_STORE = Path("var/events/events.jsonl")


@dataclass
class Event:
    event: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _store_path() -> Path:
    path = DEFAULT_EVENT_STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def serialize_event(event: Event) -> dict[str, Any]:
    payload = asdict(event)
    # ensure metadata serializable
    payload["metadata"] = payload.get("metadata", {})
    return payload


def track_event(
    event: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Event:
    evt = Event(
        event=event,
        user_id=user_id,
        session_id=session_id,
        source=source,
        metadata=metadata or {},
    )
    path = _store_path()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(serialize_event(evt), ensure_ascii=False) + "\n")
    return evt


__all__ = ["Event", "track_event", "serialize_event", "DEFAULT_EVENT_STORE"]
