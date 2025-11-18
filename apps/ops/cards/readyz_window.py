"""Readyz window burst card for operations dashboard.

Provides real-time visibility into readyz health window with burst detection.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

from apps.metrics.registry import METRICS


@dataclass
class ReadyzWindowEntry:
    """Single readyz check entry."""

    timestamp: float
    ok: bool
    reasons: List[str]  # Failure reason codes


class ReadyzWindowTracker:
    """Track readyz check history in sliding window."""

    def __init__(self, window_sec: float = 300, max_samples: int = 300):
        self.window_sec = window_sec
        self.history: Deque[ReadyzWindowEntry] = deque(maxlen=max_samples)
        self._burst_count = 0

    def record(self, ok: bool, reasons: Optional[List[str]] = None) -> None:
        """Record readyz check result."""
        entry = ReadyzWindowEntry(
            timestamp=time.time(),
            ok=ok,
            reasons=reasons or [],
        )
        self.history.append(entry)

        # Update burst count
        if not ok:
            self._burst_count += 1
        else:
            self._burst_count = 0

    def _trim_window(self) -> None:
        """Remove entries outside the time window."""
        cutoff = time.time() - self.window_sec
        while self.history and self.history[0].timestamp < cutoff:
            self.history.popleft()

    def get_window_stats(self) -> Dict:
        """Get statistics for current window."""
        self._trim_window()

        total = len(self.history)
        if total == 0:
            return {
                "samples": 0,
                "ok": 0,
                "fail": 0,
                "fail_ratio": 0.0,
                "burst_current": 0,
                "burst_max": 0,
                "window_sec": self.window_sec,
            }

        fail_count = sum(1 for e in self.history if not e.ok)
        ok_count = total - fail_count

        # Calculate max burst in window
        max_burst = 0
        current_burst = 0
        for entry in self.history:
            if not entry.ok:
                current_burst += 1
                max_burst = max(max_burst, current_burst)
            else:
                current_burst = 0

        return {
            "samples": total,
            "ok": ok_count,
            "fail": fail_count,
            "fail_ratio": round(fail_count / total, 4),
            "burst_current": self._burst_count,
            "burst_max": max_burst,
            "window_sec": self.window_sec,
        }

    def get_failure_reasons(self, limit: int = 10) -> List[Dict]:
        """Get recent failure reasons."""
        self._trim_window()

        failures = [e for e in self.history if not e.ok][-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "age_seconds": int(time.time() - e.timestamp),
                "reasons": e.reasons,
            }
            for e in failures
        ]

    def get_reason_distribution(self) -> Dict[str, int]:
        """Get distribution of failure reasons."""
        self._trim_window()

        distribution: Dict[str, int] = {}
        for entry in self.history:
            if not entry.ok:
                for reason in entry.reasons:
                    distribution[reason] = distribution.get(reason, 0) + 1

        return distribution


# Global tracker
_TRACKER = ReadyzWindowTracker()


def record_readyz_check(ok: bool, reasons: Optional[List[str]] = None) -> None:
    """Record readyz check for tracking."""
    _TRACKER.record(ok, reasons)


def get_readyz_window_card() -> Dict:
    """Generate readyz window burst card.

    Returns:
        Card with window stats, burst info, and alerts
    """
    stats = _TRACKER.get_window_stats()
    failures = _TRACKER.get_failure_reasons(limit=5)
    reason_dist = _TRACKER.get_reason_distribution()

    # Determine health and alerts
    health = "healthy"
    alerts = []

    if stats["samples"] == 0:
        health = "unknown"
        alerts.append("No readyz checks in window")
    elif stats["burst_current"] >= 5:
        health = "critical"
        alerts.append(f"Burst: {stats['burst_current']} consecutive failures")
    elif stats["burst_current"] >= 3:
        health = "warning"
        alerts.append(f"Burst: {stats['burst_current']} consecutive failures")
    elif stats["fail_ratio"] > 0.1:
        health = "degraded"
        alerts.append(f"Failure rate: {stats['fail_ratio'] * 100:.1f}%")

    # Top failure reasons
    top_reasons = sorted(reason_dist.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "card_type": "readyz_window",
        "timestamp": time.time(),
        "health": health,
        "alerts": alerts,
        "window": stats,
        "recent_failures": failures,
        "top_reasons": [
            {"reason": reason, "count": count} for reason, count in top_reasons
        ],
    }


async def get_readyz_metrics_summary() -> Dict:
    """Get readyz metrics summary from registry.

    Returns:
        Summary of readyz metrics
    """
    # Export metrics and parse
    metrics_text = METRICS.export_prom_text()

    # Parse relevant metrics
    ready_count = 0
    degraded_count = 0
    reason_counts: Dict[str, int] = {}

    for line in metrics_text.split("\n"):
        if "decisionos_readyz_total" in line:
            if 'result="ready"' in line:
                ready_count = int(line.split()[-1])
            elif 'result="degraded"' in line:
                degraded_count = int(line.split()[-1])
        elif "decisionos_readyz_reason_total" in line:
            # Extract check and code
            if 'check="' in line and 'code="' in line:
                parts = line.split("{")[1].split("}")[0]
                count = int(line.split()[-1])
                reason_counts[parts] = count

    total = ready_count + degraded_count
    ready_ratio = (ready_count / total * 100) if total > 0 else 0

    return {
        "checks": {
            "ready": ready_count,
            "degraded": degraded_count,
            "total": total,
            "ready_ratio": round(ready_ratio, 2),
        },
        "reason_distribution": reason_counts,
    }
