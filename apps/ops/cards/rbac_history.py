"""RBAC ETag history card for operations dashboard.

Provides visibility into RBAC map changes and reload history.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List

from apps.metrics.registry import METRICS


@dataclass
class RBACHistoryEntry:
    """Single RBAC map reload entry."""

    etag: str
    timestamp: float
    event: str  # "reload" | "initial"


class RBACHistoryTracker:
    """Track RBAC map reload history."""

    def __init__(self, max_entries: int = 50):
        self.history: Deque[RBACHistoryEntry] = deque(maxlen=max_entries)
        self._current_etag: str = ""

    def record_reload(self, etag: str, event: str = "reload") -> None:
        """Record a reload event."""
        if etag != self._current_etag:
            entry = RBACHistoryEntry(
                etag=etag,
                timestamp=time.time(),
                event=event,
            )
            self.history.append(entry)
            self._current_etag = etag

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent history entries."""
        entries = list(self.history)[-limit:]
        return [
            {
                "etag": e.etag[:16],  # First 16 chars
                "etag_full": e.etag,
                "timestamp": e.timestamp,
                "event": e.event,
                "age_seconds": int(time.time() - e.timestamp),
            }
            for e in entries
        ]

    def get_current_etag(self) -> str:
        """Get current ETag."""
        return self._current_etag

    def get_stats(self) -> Dict:
        """Get statistics."""
        total_reloads = len(self.history)
        unique_etags = len(set(e.etag for e in self.history))

        if total_reloads > 1:
            # Calculate reload rate (reloads per hour)
            first = self.history[0]
            last = self.history[-1]
            duration_hours = (last.timestamp - first.timestamp) / 3600
            reload_rate = (total_reloads - 1) / duration_hours if duration_hours > 0 else 0
        else:
            reload_rate = 0

        return {
            "total_reloads": total_reloads,
            "unique_etags": unique_etags,
            "reload_rate_per_hour": round(reload_rate, 2),
            "current_etag": self._current_etag[:16] if self._current_etag else "EMPTY",
            "current_etag_full": self._current_etag,
        }


# Global tracker
_TRACKER = RBACHistoryTracker()


def record_rbac_reload(etag: str, event: str = "reload") -> None:
    """Record RBAC reload for tracking."""
    _TRACKER.record_reload(etag, event)


def get_rbac_history_card(limit: int = 20) -> Dict:
    """Generate RBAC history card.

    Returns:
        Card with history, stats, and health status
    """
    history = _TRACKER.get_history(limit)
    stats = _TRACKER.get_stats()

    # Determine health
    if stats["total_reloads"] == 0:
        health = "unknown"
        health_message = "No reload history"
    elif stats["reload_rate_per_hour"] > 10:
        health = "warning"
        health_message = f"High reload rate: {stats['reload_rate_per_hour']}/hr"
    elif stats["current_etag"] == "EMPTY":
        health = "error"
        health_message = "No RBAC map loaded"
    else:
        health = "healthy"
        health_message = "Normal reload activity"

    return {
        "card_type": "rbac_history",
        "timestamp": time.time(),
        "health": health,
        "health_message": health_message,
        "stats": stats,
        "history": history,
    }


async def get_rbac_metrics_summary() -> Dict:
    """Get RBAC metrics summary from registry.

    Returns:
        Summary of RBAC metrics
    """
    # Export metrics and parse
    metrics_text = METRICS.export_prom_text()

    # Parse relevant metrics
    route_match_hit = 0
    route_match_miss = 0
    eval_allow = 0
    eval_deny = 0
    eval_bypass = 0

    for line in metrics_text.split("\n"):
        if "decisionos_rbac_route_match_total" in line:
            if 'match="hit"' in line:
                route_match_hit = int(line.split()[-1])
            elif 'match="miss"' in line:
                route_match_miss = int(line.split()[-1])
        elif "decisionos_rbac_eval_total" in line:
            if 'result="allow"' in line:
                eval_allow = int(line.split()[-1])
            elif 'result="deny"' in line:
                eval_deny = int(line.split()[-1])
            elif 'result="bypass"' in line:
                eval_bypass = int(line.split()[-1])

    total_match = route_match_hit + route_match_miss
    total_eval = eval_allow + eval_deny

    match_rate = (route_match_hit / total_match * 100) if total_match > 0 else 0
    approval_rate = (eval_allow / total_eval * 100) if total_eval > 0 else 0

    return {
        "route_match": {
            "hit": route_match_hit,
            "miss": route_match_miss,
            "total": total_match,
            "hit_rate": round(match_rate, 2),
        },
        "eval": {
            "allow": eval_allow,
            "deny": eval_deny,
            "bypass": eval_bypass,
            "total": total_eval,
            "approval_rate": round(approval_rate, 2),
        },
    }
