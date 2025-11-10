"""Event SDK and collector utilities for Gate-L."""

from .sdk import Event, track_event, DEFAULT_EVENT_STORE
from .collector import append_event, iter_events, stats_by_event

__all__ = [
    "Event",
    "track_event",
    "DEFAULT_EVENT_STORE",
    "append_event",
    "iter_events",
    "stats_by_event",
]

