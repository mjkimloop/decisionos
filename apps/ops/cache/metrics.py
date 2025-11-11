from __future__ import annotations
from typing import Dict, Any
import time

class ETagStoreMetrics:
    """ETag 저장소 메트릭 수집기"""
    def __init__(self):
        self._hits = 0
        self._misses = 0
        self._puts = 0
        self._errors = 0
        self._last_reset = time.time()

    def record_hit(self):
        """캐시 히트 기록"""
        self._hits += 1

    def record_miss(self):
        """캐시 미스 기록"""
        self._misses += 1

    def record_put(self):
        """캐시 저장 기록"""
        self._puts += 1

    def record_error(self):
        """에러 기록"""
        self._errors += 1

    def get_stats(self) -> Dict[str, Any]:
        """현재 메트릭 반환"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        uptime = time.time() - self._last_reset

        return {
            "hits": self._hits,
            "misses": self._misses,
            "puts": self._puts,
            "errors": self._errors,
            "total_requests": total_requests,
            "hit_rate_pct": round(hit_rate, 2),
            "uptime_sec": round(uptime, 2),
        }

    def reset(self):
        """메트릭 초기화"""
        self._hits = 0
        self._misses = 0
        self._puts = 0
        self._errors = 0
        self._last_reset = time.time()


# 전역 메트릭 인스턴스
_METRICS = ETagStoreMetrics()

def get_metrics() -> ETagStoreMetrics:
    """전역 메트릭 인스턴스 반환"""
    return _METRICS
