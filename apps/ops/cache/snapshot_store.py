from __future__ import annotations

import json
import os
import time
from typing import Optional, Tuple

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

# v0.5.11u-7: Compression support
from apps.common.compress import should_compress, gzip_bytes, gunzip_bytes

_SNAPSHOT_COMPRESS = os.getenv("DECISIONOS_SNAPSHOT_COMPRESS", "1") in ("1", "true", "yes")


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
                # v0.5.11u-7: Auto-decompress if compressed
                if isinstance(v, bytes) and _SNAPSHOT_COMPRESS:
                    try:
                        v = gunzip_bytes(v).decode("utf-8")
                    except Exception:
                        # Not compressed or decompression failed, treat as JSON string
                        if isinstance(v, bytes):
                            v = v.decode("utf-8")

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
        payload = json.dumps({"body": body, "ts": ts})

        if self._r:
            # v0.5.11u-7: Compress before storing in Redis
            if _SNAPSHOT_COMPRESS and should_compress(len(payload)):
                payload_bytes = gzip_bytes(payload.encode("utf-8"))
            else:
                payload_bytes = payload.encode("utf-8")
            self._r.setex(key, self._ttl, payload_bytes)
        else:
            self._mem[key] = (body, ts)

    def delete(self, key: str):
        if self._r:
            self._r.delete(key)
        self._mem.pop(key, None)
