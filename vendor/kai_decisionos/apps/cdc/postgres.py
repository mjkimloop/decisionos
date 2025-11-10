from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Dict, Any


@dataclass
class CDCEvent:
    table: str
    operation: str
    payload: Dict[str, Any]


class PostgresCDC:
    def __init__(self, dsn: str, slot: str = "decisionos_slot") -> None:
        self.dsn = dsn
        self.slot = slot

    def stream(self, handler: Callable[[CDCEvent], None], limit: int = 10) -> int:
        # Stub: generate fake events
        count = 0
        for idx in range(limit):
            event = CDCEvent(
                table="leads",
                operation="INSERT",
                payload={"id": f"lead-{idx}", "score": idx},
            )
            handler(event)
            count += 1
        return count


__all__ = ["PostgresCDC", "CDCEvent"]
