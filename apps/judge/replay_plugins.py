from __future__ import annotations

import os
import sqlite3
import time
from abc import ABC, abstractmethod

try:  # optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

TTL_SEC = 600
SKEW_SEC = 120


class ReplayStoreABC(ABC):
    """Replay store 인터페이스."""

    @abstractmethod
    def seen_or_insert(self, key_id: str, nonce: str, ts_epoch: int) -> bool:
        """True 반환 시 재사용/유효범위 밖 → fail-closed."""

    def purge_expired(self) -> None:  # pragma: no cover - optional
        """선택적 정리 훅."""

    def close(self) -> None:  # pragma: no cover - optional
        """선택적 종료 훅."""


class SQLiteReplayStore(ReplayStoreABC):
    def __init__(self, path: str = "var/judge/replay.sqlite") -> None:
        if path != ":memory:":
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
        self._conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nonce_log(
                key_id TEXT NOT NULL,
                nonce TEXT NOT NULL,
                ts INTEGER NOT NULL,
                PRIMARY KEY(key_id, nonce)
            )
            """
        )
        self._conn.commit()

    def seen_or_insert(self, key_id: str, nonce: str, ts_epoch: int) -> bool:
        now = int(time.time())
        if abs(now - ts_epoch) > SKEW_SEC + TTL_SEC:
            return True
        try:
            self._conn.execute(
                "INSERT INTO nonce_log(key_id, nonce, ts) VALUES (?,?,?)",
                (key_id, nonce, ts_epoch),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            return True
        self._conn.execute("DELETE FROM nonce_log WHERE ? - ts > ?", (now, TTL_SEC))
        self._conn.commit()
        return False

    def close(self) -> None:  # pragma: no cover
        try:
            self._conn.close()
        except Exception:
            pass


class RedisReplayStore(ReplayStoreABC):
    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        if redis is None:
            raise RuntimeError("redis package not installed")
        self._client = redis.from_url(url)

    def seen_or_insert(self, key_id: str, nonce: str, ts_epoch: int) -> bool:
        now = int(time.time())
        if abs(now - ts_epoch) > SKEW_SEC + TTL_SEC:
            return True
        key = f"judge:nonce:{key_id}:{nonce}"
        try:
            inserted = self._client.set(key, ts_epoch, nx=True, ex=TTL_SEC)
        except Exception:
            return True
        return not bool(inserted)


__all__ = [
    "ReplayStoreABC",
    "SQLiteReplayStore",
    "RedisReplayStore",
    "TTL_SEC",
    "SKEW_SEC",
]
