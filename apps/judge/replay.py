from __future__ import annotations

from .replay_plugins import RedisReplayStore, ReplayStoreABC, SQLiteReplayStore


class ReplayStore(SQLiteReplayStore):
    """Backward compatible alias (기본 SQLite 구현)."""


__all__ = [
    "ReplayStore",
    "ReplayStoreABC",
    "SQLiteReplayStore",
    "RedisReplayStore",
]
