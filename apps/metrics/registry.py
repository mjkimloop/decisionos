"""Lightweight metrics registry for Prometheus text format export.

Provides in-memory counters for observability without heavy dependencies.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Tuple


class _Counter:
    """Thread-safe counter with label support."""

    def __init__(self):
        self._vals: Dict[Tuple[Tuple[str, str], ...], int] = {}
        self._lock = asyncio.Lock()

    async def inc(self, labels: Dict[str, str] | None = None, n: int = 1):
        """Increment counter with optional labels."""
        key = tuple(sorted((labels or {}).items()))
        async with self._lock:
            self._vals[key] = self._vals.get(key, 0) + n

    def snapshot(self):
        """Get current counter values."""
        return dict(self._vals)


class MetricRegistry:
    """Lightweight metrics registry for Prometheus."""

    def __init__(self):
        self.counters: Dict[str, _Counter] = {
            "decisionos_rbac_eval_total": _Counter(),
            "decisionos_rbac_hotreload_total": _Counter(),
            "decisionos_pii_masked_strings_total": _Counter(),
            "decisionos_etag_requests_total": _Counter(),  # outcome=hit|miss
            "decisionos_etag_delta_total": _Counter(),  # outcome=delta_hit|delta_miss
            "decisionos_rbac_map_reload_total": _Counter(),
            "decisionos_readyz_total": _Counter(),
            "decisionos_readyz_reason_total": _Counter(),
        }
        self.gauges: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = {}

    async def inc(self, name: str, labels: Dict[str, str] | None = None, n: int = 1):
        """Increment counter by name."""
        if name not in self.counters:
            self.counters[name] = _Counter()
        await self.counters[name].inc(labels, n)

    def inc_sync(self, name: str, labels: Dict[str, str] | None = None, n: int = 1):
        """Synchronous increment helper for non-async contexts."""
        if name not in self.counters:
            self.counters[name] = _Counter()
        key = tuple(sorted((labels or {}).items()))
        self.counters[name]._vals[key] = self.counters[name]._vals.get(key, 0) + n

    def set_sync(self, name: str, value: float, labels: Dict[str, str] | None = None):
        key = tuple(sorted((labels or {}).items()))
        if name not in self.gauges:
            self.gauges[name] = {}
        self.gauges[name][key] = value

    def export_prom_text(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        for name, ctr in self.counters.items():
            snap = ctr.snapshot()
            for lbls, val in snap.items():
                if lbls:
                    lab = ",".join(f'{k}="{v}"' for k, v in lbls)
                    lines.append(f"{name}{{{lab}}} {val}")
                else:
                    lines.append(f"{name} {val}")
        for name, gauge in self.gauges.items():
            for lbls, val in gauge.items():
                if lbls:
                    lab = ",".join(f'{k}="{v}"' for k, v in lbls)
                    lines.append(f"{name}{{{lab}}} {val}")
                else:
                    lines.append(f"{name} {val}")
        return "\n".join(lines) + "\n"


# Global registry
METRICS = MetricRegistry()


# Helper for RBAC hotreload tracking
async def mark_rbac_reload(hit: bool):
    """Mark RBAC hotreload hit/miss."""
    await METRICS.inc("decisionos_rbac_hotreload_total", {"result": "hit" if hit else "miss"})
