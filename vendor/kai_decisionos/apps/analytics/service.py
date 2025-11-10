from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from apps.events.collector import iter_events, stats_by_event


def summarise_events(limit: int | None = None) -> Dict[str, object]:
    events: List[Dict] = list(iter_events(limit=limit))
    counter = Counter(evt.get("event", "unknown") for evt in events)
    by_source = Counter(evt.get("source", "unknown") for evt in events)
    return {
        "total": sum(counter.values()),
        "by_event": dict(counter),
        "by_source": dict(by_source),
        "sample": events[:10],
    }


def dashboard_html(summary: Dict[str, object]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    body = ["<html><head><title>DecisionOS Analytics</title></head><body>"]
    body.append(f"<h1>DecisionOS Analytics Dashboard</h1><p>Generated: {now}</p>")
    body.append("<h2>Totals</h2>")
    body.append(f"<pre>{json.dumps(summary, ensure_ascii=False, indent=2)}</pre>")
    body.append("</body></html>")
    return "".join(body)


def summary_counts() -> Dict[str, int]:
    return stats_by_event()


__all__ = ["summarise_events", "dashboard_html", "summary_counts"]
