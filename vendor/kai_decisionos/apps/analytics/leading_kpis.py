from __future__ import annotations

from typing import Iterable, Tuple


def compute_leading_kpis(rows: Iterable[dict], label_key: str = "converted") -> dict:
    total = 0
    positives = 0
    for r in rows:
        total += 1
        if r.get(label_key) in (1, True, "1", "true", "True"):
            positives += 1
    rate = 0.0 if total == 0 else round(positives / total, 4)
    return {"n": total, "positive_rate": rate}

