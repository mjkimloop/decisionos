from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


def parse_settlement_file(path: Path) -> List[dict]:
    rows: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cols = line.split(",")
        rows.append(
            {
                "charge_id": cols[0],
                "amount": int(cols[1]),
                "currency": cols[2] if len(cols) > 2 else "KRW",
                "status": cols[3] if len(cols) > 3 else "posted",
            }
        )
    return rows


__all__ = ["parse_settlement_file"]
