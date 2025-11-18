from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

ETAG_TTL_SEC_DEFAULT = int(os.getenv("DECISIONOS_ETAG_TTL_SEC", "86400"))


def etag_v2_key(tenant: str, route: str, etag_key: str) -> str:
    base = f"{tenant}:{route}:{etag_key}"
    return hashlib.sha256(base.encode()).hexdigest()


@dataclass
class ETagValue:
    etag: str
    last_modified: float


class BaseETagStore:
    def get(self, k: str) -> Optional[ETagValue]:
        raise NotImplementedError

    def set(self, k: str, v: ETagValue, ttl: int = ETAG_TTL_SEC_DEFAULT) -> None:
        raise NotImplementedError

    def invalidate_prefix(self, prefix: str) -> int:
        raise NotImplementedError

    def now(self) -> float:
        return time.time()


class InMemoryETagStore(BaseETagStore):
    def __init__(self) -> None:
        self._db: Dict[str, Tuple[ETagValue, float]] = {}

    def get(self, k: str) -> Optional[ETagValue]:
        rec = self._db.get(k)
        if not rec:
            return None
        value, expires_at = rec
        if expires_at and expires_at < self.now():
            self._db.pop(k, None)
            return None
        return value

    def set(self, k: str, v: ETagValue, ttl: int = ETAG_TTL_SEC_DEFAULT) -> None:
        self._db[k] = (v, self.now() + ttl if ttl else 0.0)

    def invalidate_prefix(self, prefix: str) -> int:
        keys = [key for key in self._db if key.startswith(prefix)]
        for key in keys:
            self._db.pop(key, None)
        return len(keys)


class RedisETagStore(BaseETagStore):
    def __init__(self, dsn: Optional[str] = None) -> None:
        if not redis or not dsn:
            self._r = None
            self._fallback = InMemoryETagStore()
        else:
            self._r = redis.Redis.from_url(dsn, decode_responses=True)  # type: ignore
            self._fallback = None

    def get(self, k: str) -> Optional[ETagValue]:
        if not self._r:
            return self._fallback.get(k)  # type: ignore
        data = self._r.hgetall(k)
        if not data:
            return None
        return ETagValue(etag=data.get("etag", ""), last_modified=float(data.get("lm", "0")))

    def set(self, k: str, v: ETagValue, ttl: int = ETAG_TTL_SEC_DEFAULT) -> None:
        if not self._r:
            self._fallback.set(k, v, ttl)  # type: ignore
            return
        pipe = self._r.pipeline()
        pipe.hset(k, mapping={"etag": v.etag, "lm": str(v.last_modified)})
        if ttl:
            pipe.expire(k, ttl)
        pipe.execute()

    def invalidate_prefix(self, prefix: str) -> int:
        if not self._r:
            return self._fallback.invalidate_prefix(prefix)  # type: ignore
        count = 0
        pattern = f"{prefix}*"
        for key in self._r.scan_iter(match=pattern):
            self._r.delete(key)
            count += 1
        return count


def build_store() -> BaseETagStore:
    """
    기본은 인메모리, DECISIONOS_ETAG_BACKEND=redis 또는 REDIS_DSN/DECISIONOS_REDIS_DSN
    제공 시 Redis 백엔드 사용.
    """
    backend = os.getenv("DECISIONOS_ETAG_BACKEND", "").lower()
    dsn = os.getenv("DECISIONOS_REDIS_DSN") or os.getenv("REDIS_DSN")
    if (backend == "redis" or dsn) and redis and dsn:
        return RedisETagStore(dsn)
    return InMemoryETagStore()


# Backward compatibility: re-export from unified storage layer
from apps.storage.etag_store import (  # noqa: E402,F401
    ETagStore as UnifiedETagStore,
    InMemoryETagStore as UnifiedInMemoryETagStore,
    RedisETagStore as UnifiedRedisETagStore,
    load_store_from_env,
)
