from __future__ import annotations

from typing import Any, Dict, List


class GoogleSheetConnector:
    name = "gsheet"

    def __init__(self, sheet_id: str, range_name: str = "A1:Z100") -> None:
        self.sheet_id = sheet_id
        self.range_name = range_name

    def fetch(self, limit: int | None = None) -> List[Dict[str, Any]]:
        rows = [
            {"sheet_id": self.sheet_id, "range": self.range_name, "row": idx}
            for idx in range(1, 6)
        ]
        if limit is not None:
            rows = rows[:limit]
        return rows


async def ingest_gsheet(sheet_id: str, range_name: str) -> int:
    connector = GoogleSheetConnector(sheet_id, range_name)
    rows = connector.fetch()
    return len(rows)


__all__ = ["GoogleSheetConnector", "ingest_gsheet"]
