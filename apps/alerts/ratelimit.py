from collections import deque
from time import time
from typing import Deque, Dict

class SlidingWindowRateLimiter:
    def __init__(self, window_sec: int, max_events: int):
        self.window = window_sec
        self.max_events = max_events
        self._buckets: Dict[str, Deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time()
        dq = self._buckets.setdefault(key, deque())
        # drop old
        cutoff = now - self.window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= self.max_events:
            return False
        dq.append(now)
        return True
