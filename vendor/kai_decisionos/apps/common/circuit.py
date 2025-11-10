from __future__ import annotations

import time
from typing import Callable, TypeVar, Generic


T = TypeVar("T")


class CircuitBreaker(Generic[T]):
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0):
        self.failure_threshold = max(1, int(failure_threshold))
        self.reset_timeout = float(reset_timeout)
        self.failures = 0
        self.opened_at: float | None = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        # half-open if timeout passed
        if (time.time() - self.opened_at) >= self.reset_timeout:
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()

