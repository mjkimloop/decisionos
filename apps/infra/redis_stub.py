from __future__ import annotations
import threading
import time
from typing import Optional

class InMemoryRedis:
    def __init__(self) -> None:
        self._data: dict[str, tuple[int | str, Optional[float]]] = {}
        self._lock = threading.Lock()

    def _cleanup(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._data.items() if exp and exp < now]
        for k in expired:
            self._data.pop(k, None)

    def get(self, key: str):
        with self._lock:
            self._cleanup()
            return self._data.get(key, (None, None))[0]

    def setex(self, key: str, ttl: int, value) -> None:
        with self._lock:
            self._data[key] = (value, time.time() + ttl if ttl else None)

    def incrby(self, key: str, amount: int = 1) -> int:
        with self._lock:
            self._cleanup()
            cur = int(self._data.get(key, (0, None))[0] or 0)
            cur += amount
            self._data[key] = (cur, None)
            return cur

    def hset(self, key: str, mapping: dict[str, str]) -> None:
        with self._lock:
            self._cleanup()
            entry = dict(self._data.get(key, ({}, None))[0] or {})
            entry.update(mapping)
            self._data[key] = (entry, None)

    def hgetall(self, key: str) -> dict:
        with self._lock:
            self._cleanup()
            entry = self._data.get(key, ({}, None))[0]
            return dict(entry) if isinstance(entry, dict) else {}

    def expire(self, key: str, ttl: int) -> None:
        with self._lock:
            if key in self._data:
                val, _ = self._data[key]
                self._data[key] = (val, time.time() + ttl if ttl else None)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def scan_iter(self, match: str):
        prefix = match.rstrip("*")
        with self._lock:
            self._cleanup()
            for key in list(self._data.keys()):
                if key.startswith(prefix):
                    yield key

    def pipeline(self):  # minimal pipeline stub
        return self

    def hset(self, key, mapping):  # type: ignore[override]
        super().hset(key, mapping)  # pragma: no cover

class RedisFacade:
    def __init__(self, client):
        self._client = client

    def __getattr__(self, item):
        return getattr(self._client, item)


def get_redis(dsn: str | None = None):
    if dsn:
        try:
            import redis  # type: ignore
            return RedisFacade(redis.from_url(dsn))
        except Exception:
            pass
    return InMemoryRedis()
