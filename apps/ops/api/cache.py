from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Tuple


@dataclass
class CacheEntry:
    etag: str
    expires_at: float
    payload: Any  # JSON dict or HTML string/bytes
    last_modified: str | None = None


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    def _now(self) -> float:
        return time.time()

    def peek(self, key: str) -> Optional[CacheEntry]:
        entry = self._store.get(key)
        if not entry:
            return None
        if entry.expires_at < self._now():
            self._store.pop(key, None)
            return None
        return entry

    def put(self, key: str, etag: str, payload: Any, ttl_sec: int, last_modified: str | None = None) -> CacheEntry:
        entry = CacheEntry(etag=etag, expires_at=self._now() + ttl_sec, payload=payload, last_modified=last_modified)
        self._store[key] = entry
        return entry

    def clear(self) -> None:
        self._store.clear()


cache = InMemoryCache()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_etag_for_json(obj: Any) -> Tuple[str, bytes]:
    blob = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"\"{_sha256_hex(blob)}\"", blob


def compute_etag_for_html(data: str | bytes) -> Tuple[str, bytes]:
    blob = data if isinstance(data, (bytes, bytearray)) else data.encode("utf-8")
    return f"\"{_sha256_hex(blob)}\"", bytes(blob)
