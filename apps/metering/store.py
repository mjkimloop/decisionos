from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Set
import sqlite3, os

class IdempoStore(ABC):
    @abstractmethod
    def seen(self, key: str) -> bool: ...
    @abstractmethod
    def mark(self, key: str) -> bool: ...
    def close(self) -> None: pass  # optional

class InMemoryIdempoStore(IdempoStore):
    def __init__(self) -> None:
        self._seen: Set[str] = set()
    def seen(self, key: str) -> bool:
        return key in self._seen
    def mark(self, key: str) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

class SQLiteIdempoStore(IdempoStore):
    """
    간단한 영속 스토어. UNIQUE(키) 충돌로 멱등을 보장.
    파일은 자동 생성되며, 다중 프로세스에서도 안전(기본 잠금).
    """
    def __init__(self, path: str = "var/metering/idempo.sqlite") -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS idempo_keys(
              k TEXT PRIMARY KEY
            )
        """)
        self._conn.commit()
    def seen(self, key: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM idempo_keys WHERE k=? LIMIT 1", (key,))
        return cur.fetchone() is not None
    def mark(self, key: str) -> bool:
        try:
            self._conn.execute("INSERT INTO idempo_keys(k) VALUES (?)", (key,))
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
