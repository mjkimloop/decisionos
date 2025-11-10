from __future__ import annotations

from collections import Counter
from typing import Iterable


def quorum_verdict(verdicts: Iterable[str], require: int = 2) -> str:
    bucket = Counter(verdicts or [])
    if not bucket:
        return "FAIL"
    top, count = bucket.most_common(1)[0]
    return top if count >= require else "FAIL"


__all__ = ["quorum_verdict"]
