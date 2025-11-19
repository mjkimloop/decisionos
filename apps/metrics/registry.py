from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple


class SlidingWindowCounter:
    def __init__(self, window_sec: int = 60):
        self.window_sec = window_sec
        self.q: Deque[Tuple[float, float]] = deque()  # (timestamp, value)

    def add(self, value: float):
        now = time.time()
        self.q.append((now, value))
        self._gc(now)

    def _gc(self, now: float):
        thr = now - self.window_sec
        while self.q and self.q[0][0] < thr:
            self.q.popleft()

    def sum(self):
        now = time.time()
        self._gc(now)
        return sum(v for _, v in self.q)

    def count(self):
        now = time.time()
        self._gc(now)
        return len(self.q)

    def p95(self):
        now = time.time()
        self._gc(now)
        vals = sorted(v for _, v in self.q)
        if not vals:
            return 0.0
        idx = int(0.95 * (len(vals) - 1))
        return vals[idx]


class MetricsRegistry:
    def __init__(self, window_sec: int = 60):
        self.window_sec = window_sec
        self.counters = defaultdict(float)  # label -> sum
        self.windows: Dict[str, SlidingWindowCounter] = defaultdict(lambda: SlidingWindowCounter(window_sec))
        self.start_time = time.time()

    def inc(self, name: str, labels: Dict[str, str] | None = None, value: float = 1.0):
        key = self._key(name, labels)
        self.counters[key] += value
        self.windows[key].add(value)

    def observe(self, name: str, labels: Dict[str, str] | None = None, value: float = 0.0):
        key = self._key(name, labels)
        self.windows[key].add(value)

    def _key(self, name: str, labels: Dict[str, str] | None = None):
        if not labels:
            return name
        parts = [f'{k}={v}' for k, v in sorted(labels.items())]
        return f"{name}|" + "|".join(parts)

    def snapshot(self):
        out = {}
        for key, win in self.windows.items():
            out[key] = {"count": win.count(), "sum": win.sum(), "p95": win.p95()}
        uptime = time.time() - self.start_time
        return {"uptime_sec": uptime, "windows": out, "counters": dict(self.counters)}

    def export_prom_text(self) -> str:
        """
        간단한 Prometheus 텍스트 포맷 노출.
        - counters: name|k=v 형식을 name{labels} value 로 노출
        - windows: p95/	count를 gauge로 노출
        """
        lines = []
        for key, val in self.counters.items():
            name, labels = self._split_key(key)
            label_str = self._format_labels(labels)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{label_str} {val}")
        for key, win in self.windows.items():
            name, labels = self._split_key(key)
            label_str = self._format_labels(labels)
            lines.append(f"# TYPE {name}_p95 gauge")
            lines.append(f"{name}_p95{label_str} {win.p95()}")
            lines.append(f"# TYPE {name}_count gauge")
            lines.append(f"{name}_count{label_str} {win.count()}")
        return "\n".join(lines) + "\n"

    def _split_key(self, key: str) -> tuple[str, Dict[str, str]]:
        if "|" not in key:
            return key, {}
        name, *label_parts = key.split("|")
        labels = {}
        for part in label_parts:
            if "=" in part:
                k, v = part.split("=", 1)
                labels[k] = v
        return name, labels

    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        items = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(items) + "}"


METRICS = MetricsRegistry()
