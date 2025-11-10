from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from .sdk import DEFAULT_EVENT_STORE, Event, serialize_event


def append_event(event: Event, store: Optional[Path] = None) -> None:
    path = (store or DEFAULT_EVENT_STORE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(serialize_event(event), ensure_ascii=False) + "\n")


def iter_events(store: Optional[Path] = None, limit: Optional[int] = None) -> Iterator[Dict]:
    path = (store or DEFAULT_EVENT_STORE)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def stats_by_event(store: Optional[Path] = None) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for evt in iter_events(store):
        name = evt.get("event", "unknown")
        counter[name] += 1
    return dict(counter)


__all__ = ["append_event", "iter_events", "stats_by_event"]
