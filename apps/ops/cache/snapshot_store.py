from __future__ import annotations

import json
import os
import time
from typing import Optional, Tuple

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


class SnapshotStore:
    def __init__(self):
        self._ttl = int(os.getenv("DECISIONOS_SNAPSHOT_TTL", "600"))
        dsn = os.getenv("DECISIONOS_REDIS_DSN", "")
        self._r = redis.Redis.from_url(dsn) if (dsn and redis) else None
        self._mem = {}

    def get(self, key: str) -> Optional[Tuple[str, float]]:
        if self._r:
            v = self._r.get(key)
            if not v:
                return None
            try:
                obj = json.loads(v)
                return obj.get("body"), float(obj.get("ts", 0))
            except Exception:
                return None
        row = self._mem.get(key)
        if not row:
            return None
        body, ts = row
        if time.time() - ts > self._ttl:
            self._mem.pop(key, None)
            return None
        return body, ts

    def set(self, key: str, body: str):
        ts = time.time()
        if self._r:
            self._r.setex(key, self._ttl, json.dumps({"body": body, "ts": ts}))
        else:
            self._mem[key] = (body, ts)

    def delete(self, key: str):
        if self._r:
            self._r.delete(key)
        self._mem.pop(key, None)
