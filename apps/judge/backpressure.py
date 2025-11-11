"""
백프레셔 및 차단 정책 표준 상수

폭주 시 시스템적 한계선 명시:
- 토큰 버킷 (초당/분당)
- 지수 백오프
- 서킷 브레이커 임계치
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import time
import threading

# 레이트 리밋 상수
RATE_LIMIT_PER_SECOND = 100  # 초당 최대 요청 수
RATE_LIMIT_PER_MINUTE = 3000  # 분당 최대 요청 수
RATE_LIMIT_BURST = 50  # 버스트 허용 수

# 지수 백오프 상수
BACKOFF_INITIAL_MS = 100  # 초기 백오프 (밀리초)
BACKOFF_MAX_MS = 30000  # 최대 백오프 (30초)
BACKOFF_MULTIPLIER = 2.0  # 백오프 배수

# 서킷 브레이커 상수
CIRCUIT_BREAKER_THRESHOLD = 10  # 연속 실패 임계치
CIRCUIT_BREAKER_TIMEOUT_SEC = 60  # 서킷 오픈 유지 시간
CIRCUIT_BREAKER_HALF_OPEN_REQUESTS = 3  # Half-Open 상태 시험 요청 수


@dataclass
class TokenBucket:
    """토큰 버킷 알고리즘 구현"""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float
    last_refill: float

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """토큰 소비 시도. 성공 시 True, 실패 시 False"""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self):
        """경과 시간에 따라 토큰 보충"""
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now

    def get_stats(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        with self._lock:
            self._refill()
            return {
                "capacity": self.capacity,
                "tokens": round(self.tokens, 2),
                "refill_rate": self.refill_rate,
                "utilization_pct": round((1 - self.tokens / self.capacity) * 100, 2)
            }


class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""
    def __init__(self, threshold: int = CIRCUIT_BREAKER_THRESHOLD,
                 timeout_sec: int = CIRCUIT_BREAKER_TIMEOUT_SEC,
                 half_open_requests: int = CIRCUIT_BREAKER_HALF_OPEN_REQUESTS):
        self.threshold = threshold
        self.timeout_sec = timeout_sec
        self.half_open_requests = half_open_requests
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed | open | half_open
        self._half_open_success_count = 0
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        with self._lock:
            state = self._get_state()

            if state == "open":
                raise Exception("Circuit breaker is OPEN")

            if state == "half_open":
                # Half-Open: 제한된 요청만 허용
                if self._half_open_success_count >= self.half_open_requests:
                    raise Exception("Circuit breaker HALF_OPEN limit reached")

        # 함수 실행
        try:
            result = func(*args, **kwargs)
            with self._lock:
                if state == "half_open":
                    self._half_open_success_count += 1
                    if self._half_open_success_count >= self.half_open_requests:
                        # Half-Open 성공 → Closed
                        self._state = "closed"
                        self._failure_count = 0
                else:
                    # Closed 상태 성공 → 실패 카운트 리셋
                    self._failure_count = 0
            return result
        except Exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()
                if self._failure_count >= self.threshold:
                    self._state = "open"
            raise e

    def _get_state(self) -> str:
        """현재 서킷 상태 반환"""
        if self._state == "open":
            # 타임아웃 경과 시 Half-Open으로 전환
            if time.time() - self._last_failure_time >= self.timeout_sec:
                self._state = "half_open"
                self._half_open_success_count = 0
        return self._state

    def get_stats(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        with self._lock:
            state = self._get_state()
            return {
                "state": state,
                "failure_count": self._failure_count,
                "threshold": self.threshold,
                "last_failure_age_sec": round(time.time() - self._last_failure_time, 2) if self._last_failure_time > 0 else None
            }


def calculate_backoff_ms(attempt: int) -> int:
    """지수 백오프 계산"""
    backoff = BACKOFF_INITIAL_MS * (BACKOFF_MULTIPLIER ** attempt)
    return min(int(backoff), BACKOFF_MAX_MS)
