from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

_ETAG_LOCK = threading.RLock()


@dataclass(frozen=True)
class _Key:
    path: str
    mtime_ns: int
    size: int
    salt: str  # tenant + catalog + query_fingerprint 등


class ETagCalcCache:
    """
    간단한 in-memory LRU 비슷한 캐시(사이즈 제한 + TTL). Redis 백엔드는 ETagStore가 대신함.
    """

    def __init__(self, max_items: int = 512, ttl_sec: int = 300):
        self.max_items = max_items
        self.ttl = ttl_sec
        self._store: Dict[_Key, Tuple[str, float]] = {}  # key -> (etag, expires_at)

    def get(self, key: _Key) -> Optional[str]:
        now = time.time()
        with _ETAG_LOCK:
            v = self._store.get(key)
            if not v:
                return None
            etag, exp = v
            if exp < now:
                self._store.pop(key, None)
                return None
            return etag

    def put(self, key: _Key, etag: str) -> None:
        with _ETAG_LOCK:
            if len(self._store) >= self.max_items:
                for k in list(self._store.keys())[: self.max_items // 4]:
                    self._store.pop(k, None)
            self._store[key] = (etag, time.time() + self.ttl)


_default_cache = ETagCalcCache(
    max_items=int(os.getenv("DECISIONOS_ETAG_CACHE_ITEMS", "512")),
    ttl_sec=int(os.getenv("DECISIONOS_ETAG_CACHE_TTL_SEC", "300")),
)


def _fast_fingerprint(path: str) -> Tuple[int, int]:
    st = os.stat(path)
    return st.st_mtime_ns, st.st_size


def compute_strong_etag(path: str, salt: str, chunk_size: int = 1024 * 1024) -> str:
    """
    salt: 테넌트/카탈로그 SHA/쿼리 해시 등을 포함하여 충돌 방지
    정책:
      - 캐시 키: (path, mtime_ns, size, salt)
      - 미스 시 파일 chunk 해시(SHA256) → ETag = sha256(hex)[0:16] + '-v2'
    """
    mtime_ns, size = _fast_fingerprint(path)
    key = _Key(path=path, mtime_ns=mtime_ns, size=size, salt=salt)
    cached = _default_cache.get(key)
    if cached:
        return cached

    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    digest = h.hexdigest()[:16] + "-v2"
    _default_cache.put(key, digest)
    return digest
