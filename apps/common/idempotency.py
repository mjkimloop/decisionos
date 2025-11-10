from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class IdempotencyRecord:
    key: str
    response: dict
    created_at: float


class IdempotencyStore:
    def __init__(self) -> None:
        self._records: Dict[str, IdempotencyRecord] = {}

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        record = self._records.get(key)
        if record and time.time() - record.created_at > 3600:
            self._records.pop(key, None)
            return None
        return record

    def set(self, key: str, response: dict) -> IdempotencyRecord:
        record = IdempotencyRecord(key=key, response=response, created_at=time.time())
        self._records[key] = record
        return record


GLOBAL_IDEMPOTENCY_STORE = IdempotencyStore()

__all__ = ["IdempotencyStore", "GLOBAL_IDEMPOTENCY_STORE", "IdempotencyRecord"]
