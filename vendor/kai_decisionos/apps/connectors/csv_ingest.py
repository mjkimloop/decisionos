from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List


class CSVConnector:
    name = "csv"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def fetch(self, limit: int | None = None) -> List[Dict[str, Any]]:
        import csv

        if not self.path.exists():
            raise FileNotFoundError(self.path)
        rows = list(csv.DictReader(self.path.open("r", encoding="utf-8")))
        if limit is not None:
            rows = rows[:limit]
        return rows


async def ingest_csv(path: Path) -> int:
    connector = CSVConnector(path)
    rows = connector.fetch()
    return len(rows)


__all__ = ["CSVConnector", "ingest_csv"]
