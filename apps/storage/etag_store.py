from __future__ import annotations
from typing import Optional
import os
import time

try:
    import redis  # optional
except Exception:
    redis = None

class ETagStore:
    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError
    def set(self, key: str, etag: str, ttl: Optional[int]=None) -> None:
        raise NotImplementedError
    def compare_and_set(self, key: str, old: Optional[str], new: str, ttl: Optional[int]=None) -> bool:
        raise NotImplementedError

class InMemoryETagStore(ETagStore):
    def __init__(self):
        self._m = {}

    def get(self, key: str) -> Optional[str]:
        rec = self._m.get(key)
        if not rec:
            return None
        etag, exp = rec
        if exp and exp < time.time():
            self._m.pop(key, None)
            return None
        return etag

    def set(self, key: str, etag: str, ttl: Optional[int]=None) -> None:
        exp = time.time()+ttl if ttl else None
        self._m[key] = (etag, exp)

    def compare_and_set(self, key: str, old: Optional[str], new: str, ttl: Optional[int]=None) -> bool:
        cur = self.get(key)
        if cur != old:
            return False
        self.set(key, new, ttl)
        return True

class RedisETagStore(ETagStore):
    def __init__(self, dsn: str):
        if not redis:
            raise RuntimeError("redis not available")
        self._r = redis.Redis.from_url(dsn, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        return self._r.get(key)

    def set(self, key: str, etag: str, ttl: Optional[int]=None) -> None:
        if ttl:
            self._r.setex(key, ttl, etag)
        else:
            self._r.set(key, etag)

    def compare_and_set(self, key: str, old: Optional[str], new: str, ttl: Optional[int]=None) -> bool:
        with self._r.pipeline() as p:
            p.watch(key)
            cur = p.get(key)
            if cur != (old if old is not None else cur):
                p.reset()
                return False
            p.multi()
            if ttl:
                p.setex(key, ttl, new)
            else:
                p.set(key, new)
            p.execute()
            return True

def load_store_from_env() -> ETagStore:
    backend = os.getenv("DECISIONOS_ETAG_BACKEND", "memory").lower()
    if backend == "redis":
        dsn = os.getenv("REDIS_DSN")
        if not dsn:
            raise RuntimeError("REDIS_DSN missing")
        return RedisETagStore(dsn)
    return InMemoryETagStore()
