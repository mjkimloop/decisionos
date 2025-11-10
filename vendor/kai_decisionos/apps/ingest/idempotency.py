from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict


class IdempotencyStore:
    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    def check_and_set(self, key: str) -> bool:
        if key in self._store:
            return False
        self._store[key] = datetime.now(timezone.utc).isoformat()
        return True

    def entries(self) -> Dict[str, str]:
        return dict(self._store)


store = IdempotencyStore()


__all__ = ["IdempotencyStore", "store"]
