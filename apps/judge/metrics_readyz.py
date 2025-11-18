# apps/judge/metrics_readyz.py
from __future__ import annotations
import threading
import time
from collections import deque
from typing import Dict

from apps.common.metrics import REG


class ReadyzMetrics:
    def __init__(self, window_1m: int = 60, window_5m: int = 300):
        self._lock = threading.Lock()
        self.total = 0
        self.fail = 0
        self.last_status = "unknown"
        self.last_ts = 0
        # Sliding windows: (timestamp, ok)
        self._window_1m: deque = deque()
        self._window_5m: deque = deque()
        self._window_1m_sec = window_1m
        self._window_5m_sec = window_5m

    def observe(self, ok: bool):
        now = time.time()
        with self._lock:
            self.total += 1
            self.fail += 0 if ok else 1
            self.last_status = "ready" if ok else "degraded"
            self.last_ts = int(now)
            # Append to sliding windows
            self._window_1m.append((now, ok))
            self._window_5m.append((now, ok))
            # Trim old entries
            self._trim_window(self._window_1m, now - self._window_1m_sec)
            self._trim_window(self._window_5m, now - self._window_5m_sec)

    def _trim_window(self, win: deque, cutoff: float):
        while win and win[0][0] < cutoff:
            win.popleft()

    def snapshot(self) -> Dict[str, int | str]:
        with self._lock:
            return {
                "total": self.total,
                "fail": self.fail,
                "last_status": self.last_status,
                "last_ts": self.last_ts,
            }

    def ratios(self) -> Dict[str, float]:
        now = time.time()
        with self._lock:
            self._trim_window(self._window_1m, now - self._window_1m_sec)
            self._trim_window(self._window_5m, now - self._window_5m_sec)
            total_1m = len(self._window_1m)
            total_5m = len(self._window_5m)
            ok_1m = sum(1 for _, ok in self._window_1m if ok)
            ok_5m = sum(1 for _, ok in self._window_5m if ok)
            ratio_1m = ok_1m / total_1m if total_1m > 0 else 1.0
            ratio_5m = ok_5m / total_5m if total_5m > 0 else 1.0
        return {"success_ratio_1m": ratio_1m, "success_ratio_5m": ratio_5m}

    def export_gauges(self):
        """Export sliding window success ratios to global metrics registry."""
        now = time.time()
        with self._lock:
            self._trim_window(self._window_1m, now - self._window_1m_sec)
            self._trim_window(self._window_5m, now - self._window_5m_sec)
            total_1m = len(self._window_1m)
            total_5m = len(self._window_5m)
            ok_1m = sum(1 for _, ok in self._window_1m if ok)
            ok_5m = sum(1 for _, ok in self._window_5m if ok)
            ratio_1m = ok_1m / total_1m if total_1m > 0 else 1.0
            ratio_5m = ok_5m / total_5m if total_5m > 0 else 1.0
        # Set gauges
        REG.gauge("readyz_success_ratio_1m", "Readyz success ratio over 1 minute").set(ratio_1m)
        REG.gauge("readyz_success_ratio_5m", "Readyz success ratio over 5 minutes").set(ratio_5m)


READYZ_METRICS = ReadyzMetrics()
