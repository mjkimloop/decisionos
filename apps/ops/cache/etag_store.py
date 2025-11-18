from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Optional, Tuple


class ETagStore:
    def get(self, key: str) -> Optional[Tuple[str, dict, float]]:
        raise NotImplementedError

    def set(self, key: str, etag: str, payload: dict, ttl_sec: int = 300) -> None:
        raise NotImplementedError

    def compute_etag(self, payload: dict, extra: str = "") -> str:
        h = hashlib.sha256()
        h.update(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        if extra:
            h.update(extra.encode())
        return h.hexdigest()


class InMemoryETagStore(ETagStore):
    def __init__(self):
        self._m = {}  # key -> (etag, payload_json_str, exp_ts)

    def get(self, key: str):
        v = self._m.get(key)
        if not v:
            return None
        etag, s, exp = v
        if exp and exp < time.time():
            self._m.pop(key, None)
            return None
        return etag, json.loads(s), exp

    def set(self, key: str, etag: str, payload: dict, ttl_sec: int = 300):
        self._m[key] = (
            etag,
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            time.time() + ttl_sec if ttl_sec else 0,
        )


def _try_import_redis():
    try:
        import redis  # type: ignore

        return redis
    except Exception:
        return None


class RedisETagStore(ETagStore):
    def __init__(self, url: str):
        rmod = _try_import_redis()
        if not rmod:
            raise RuntimeError("redis-py not installed")
        self.r = rmod.from_url(url, decode_responses=True)
        self.prefix = os.getenv("DECISIONOS_ETAG_PREFIX", "decisionos:etag:")

    def _k(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def get(self, key: str):
        s = self.r.get(self._k(key))
        if not s:
            return None
        obj = json.loads(s)
        if obj.get("exp") and obj["exp"] < time.time():
            self.r.delete(self._k(key))
            return None
        return obj["etag"], obj["payload"], obj.get("exp", 0)

    def set(self, key: str, etag: str, payload: dict, ttl_sec: int = 300):
        exp = time.time() + ttl_sec if ttl_sec else 0
        body = {"etag": etag, "payload": payload, "exp": exp}
        s = json.dumps(body, separators=(",", ":"), sort_keys=True)
        if ttl_sec:
            self.r.setex(self._k(key), ttl_sec, s)
        else:
            self.r.set(self._k(key), s)


def get_store() -> ETagStore:
    url = os.getenv("DECISIONOS_REDIS_URL", "").strip()
    if url:
        try:
            return RedisETagStore(url)
        except Exception:
            return InMemoryETagStore()
    return InMemoryETagStore()
