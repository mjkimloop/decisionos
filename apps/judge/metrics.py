from __future__ import annotations

import time
from collections import deque
from statistics import median
from threading import Lock
from typing import Deque, Dict, Tuple


class JudgeMetrics:
    """Sliding-window metrics for Judge infra."""

    def __init__(self, window_seconds: int = 600) -> None:
        self.window_seconds = window_seconds
        self._records: Deque[Tuple[float, float, int, bool]] = deque()
        self._lock = Lock()

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._records and self._records[0][0] < cutoff:
            self._records.popleft()

    def observe(self, latency_ms: float, status_code: int, signature_error: bool) -> None:
        now = time.time()
        with self._lock:
            self._records.append((now, latency_ms, status_code, signature_error))
            self._trim(now)

    def summary(self) -> Dict[str, object]:
        with self._lock:
            records = list(self._records)

        total = len(records)
        if not records:
            return {
                "latency_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0},
                "availability": 1.0,
                "error_rate": 0.0,
                "signature_error_rate": 0.0,
                "count": 0,
                "window": {"seconds": self.window_seconds},
            }

        latencies = sorted(r[1] for r in records)
        p50 = float(median(latencies))
        p95 = self._percentile(latencies, 0.95)
        p99 = self._percentile(latencies, 0.99)

        five_xx = sum(1 for _, _, status, _ in records if status >= 500)
        errorish = sum(1 for _, _, status, _ in records if status >= 500 or status == 429)
        sig_err = sum(1 for _, _, _, sig in records if sig)

        availability = 1.0 - (five_xx / total)
        error_rate = errorish / total
        sig_rate = sig_err / total

        return {
            "latency_ms": {"p50": round(p50, 2), "p95": round(p95, 2), "p99": round(p99, 2)},
            "availability": round(availability, 6),
            "error_rate": round(error_rate, 6),
            "signature_error_rate": round(sig_rate, 6),
            "count": total,
            "window": {"seconds": self.window_seconds},
        }

    @staticmethod
    def _percentile(sorted_values: list[float], fraction: float) -> float:
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * fraction
        f = int(k)
        c = min(f + 1, len(sorted_values) - 1)
        if f == c:
            return float(sorted_values[int(k)])
        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)
        return float(d0 + d1)


__all__ = ["JudgeMetrics"]
