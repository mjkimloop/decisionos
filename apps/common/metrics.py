"""Lightweight in-memory Prometheus-compatible metrics registry.

No external dependencies (no redis, no prometheus_client).
Thread-safe counters, gauges, and info metrics.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Tuple


class Counter:
    def __init__(self, name: str, help_text: str = ""):
        self.name = name
        self.help = help_text
        self._value = 0
        self._lock = threading.Lock()

    def inc(self, amount: int = 1):
        with self._lock:
            self._value += amount

    def get(self) -> int:
        with self._lock:
            return self._value


class Gauge:
    def __init__(self, name: str, help_text: str = ""):
        self.name = name
        self.help = help_text
        self._value = 0.0
        self._lock = threading.Lock()

    def set(self, val: float):
        with self._lock:
            self._value = val

    def inc(self, amount: float = 1.0):
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0):
        with self._lock:
            self._value -= amount

    def get(self) -> float:
        with self._lock:
            return self._value


class Info:
    """Info metric: labels only, value always 1."""

    def __init__(self, name: str, labels: Tuple[str, ...] = (), help_text: str = ""):
        self.name = name
        self.labels = labels
        self.help = help_text
        self._label_values: Tuple[str, ...] = ()
        self._lock = threading.Lock()

    def set(self, values: Tuple[str, ...]):
        with self._lock:
            self._label_values = values

    def get(self) -> Tuple[Tuple[str, ...], int]:
        with self._lock:
            return self._label_values, 1


class Registry:
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._infos: Dict[str, Info] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, help_text: str = "") -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, help_text)
            return self._counters[name]

    def gauge(self, name: str, help_text: str = "") -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, help_text)
            return self._gauges[name]

    def info(self, name: str, labels: Tuple[str, ...] = (), help_text: str = "") -> Info:
        with self._lock:
            if name not in self._infos:
                self._infos[name] = Info(name, labels, help_text)
            return self._infos[name]

    def render_text(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines = []
        with self._lock:
            for c in self._counters.values():
                if c.help:
                    lines.append(f"# HELP {c.name} {c.help}")
                lines.append(f"# TYPE {c.name} counter")
                lines.append(f"{c.name} {c.get()}")
            for g in self._gauges.values():
                if g.help:
                    lines.append(f"# HELP {g.name} {g.help}")
                lines.append(f"# TYPE {g.name} gauge")
                lines.append(f"{g.name} {g.get()}")
            for info in self._infos.values():
                if info.help:
                    lines.append(f"# HELP {info.name} {info.help}")
                lines.append(f"# TYPE {info.name} gauge")
                label_values, val = info.get()
                if label_values:
                    label_str = ",".join(f'{k}="{v}"' for k, v in zip(info.labels, label_values))
                    lines.append(f"{info.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{info.name} {val}")
        return "\n".join(lines) + "\n"


# Global singleton registry
REG = Registry()


__all__ = ["Counter", "Gauge", "Info", "Registry", "REG"]
