from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple
from .metrics import get_metrics

__all__ = [
    "ETagStore",
    "InMemoryETagStore",
    "RedisETagStore",
    "build_etag_store",
]

try:
    import redis  # type: ignore
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False


class ETagStore:
    """ETag → payload(snapshot) 저장/조회 추상 인터페이스."""
    def put(self, etag: str, payload: Dict[str, Any], ttl_sec: int = 86400) -> None:  # 1 day
        raise NotImplementedError

    def get(self, etag: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class InMemoryETagStore(ETagStore):
    """의존성 없는 인메모리 구현. 프로세스 생명주기 동안만 유효."""
    def __init__(self):
        self._lock = threading.RLock()
        # etag -> (expire_epoch, payload)
        self._data: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def put(self, etag: str, payload: Dict[str, Any], ttl_sec: int = 86400) -> None:
        exp = time.time() + float(ttl_sec)
        with self._lock:
            self._data[etag] = (exp, payload)
        get_metrics().record_put()

    def get(self, etag: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._data.get(etag)
            if not item:
                get_metrics().record_miss()
                return None
            exp, payload = item
            if exp < time.time():
                # TTL 만료 → 제거
                self._data.pop(etag, None)
                get_metrics().record_miss()
                return None
            get_metrics().record_hit()
            return payload

    def clear_expired(self) -> int:
        """만료된 항목 정리 (백그라운드 태스크용)"""
        now = time.time()
        removed = 0
        with self._lock:
            expired = [k for k, (exp, _) in self._data.items() if exp < now]
            for k in expired:
                self._data.pop(k, None)
                removed += 1
        return removed


class RedisETagStore(ETagStore):
    """Redis 기반 구현. TTL/eviction은 Redis에 위임."""
    def __init__(self, url: str, prefix: str = "dos:cards:etag", decode_responses: bool = True):
        if not _HAS_REDIS:
            raise RuntimeError("redis 라이브러리가 설치되지 않았습니다. (pip install redis)")
        # 연결
        self._r = redis.Redis.from_url(url, decode_responses=decode_responses)
        self._prefix = prefix

    def _key(self, etag: str) -> str:
        return f"{self._prefix}:{etag}"

    def put(self, etag: str, payload: Dict[str, Any], ttl_sec: int = 86400) -> None:
        try:
            # 정렬·압축된 JSON으로 저장(안정적 비교/디버깅)
            doc = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            # SET with EX(초) → TTL
            self._r.set(self._key(etag), doc, ex=int(ttl_sec))
            get_metrics().record_put()
        except Exception:
            get_metrics().record_error()
            raise

    def get(self, etag: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self._r.get(self._key(etag))
            if raw is None:
                get_metrics().record_miss()
                return None
            try:
                result = json.loads(raw)
                get_metrics().record_hit()
                return result
            except Exception:
                # 손상 데이터 방어: 키 삭제 후 None
                try:
                    self._r.delete(self._key(etag))
                finally:
                    get_metrics().record_miss()
                    return None
        except Exception:
            get_metrics().record_error()
            raise


def build_etag_store() -> ETagStore:
    """
    환경 변수로 백엔드 선택:
      - DECISIONOS_ETAG_BACKEND = "redis" | "memory"(default)
      - DECISIONOS_REDIS_URL (default: redis://localhost:6379/0)
      - DECISIONOS_ETAG_REDIS_PREFIX (default: dos:cards:etag)
    Redis 사용 불가(미설치/접속오류) 시 자동 fallback → InMemory
    """
    backend = (os.getenv("DECISIONOS_ETAG_BACKEND") or "memory").lower().strip()
    if backend == "redis":
        url = os.getenv("DECISIONOS_REDIS_URL", "redis://localhost:6379/0")
        prefix = os.getenv("DECISIONOS_ETAG_REDIS_PREFIX", "dos:cards:etag")
        if _HAS_REDIS:
            try:
                store = RedisETagStore(url=url, prefix=prefix)
                # 간단 ping으로 연결 확인(실패 시 메모리로 폴백)
                store._r.ping()
                return store
            except Exception:
                pass  # 아래 메모리 폴백
        # 폴백 로그는 상위 로거에서 처리 가능. 여기선 조용히 메모리 사용.
    return InMemoryETagStore()
