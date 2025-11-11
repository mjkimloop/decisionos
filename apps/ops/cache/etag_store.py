from __future__ import annotations
import threading, time
from typing import Any, Optional, Dict

class ETagStore:
    """ETag 스냅샷 저장소 인터페이스"""
    def put(self, etag: str, payload: Dict[str, Any], ttl_sec: int = 86400) -> None:
        """ETag와 페이로드를 TTL과 함께 저장"""
        raise NotImplementedError

    def get(self, etag: str) -> Optional[Dict[str, Any]]:
        """ETag로 저장된 페이로드 조회 (만료 시 None)"""
        raise NotImplementedError

class InMemoryETagStore(ETagStore):
    """메모리 기반 ETag 스냅샷 저장소 (프로세스 단일톤)"""
    def __init__(self):
        self._lock = threading.RLock()
        self._data: Dict[str, tuple[float, Dict[str, Any]]] = {}

    def put(self, etag: str, payload: Dict[str, Any], ttl_sec: int = 86400) -> None:
        exp = time.time() + ttl_sec
        with self._lock:
            self._data[etag] = (exp, payload)

    def get(self, etag: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._data.get(etag)
            if not item:
                return None
            exp, payload = item
            if exp < time.time():
                self._data.pop(etag, None)
                return None
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
