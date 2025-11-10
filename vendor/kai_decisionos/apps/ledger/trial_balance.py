from __future__ import annotations

from collections import defaultdict
from typing import Dict

from .postings import POSTINGS


def trial_balance() -> Dict[str, dict]:
    totals: Dict[str, dict] = defaultdict(lambda: {"debit": 0, "credit": 0})
    for posting in POSTINGS:
        totals[posting.account]["debit"] += posting.debit
        totals[posting.account]["credit"] += posting.credit
    for account, values in totals.items():
        values["net"] = values["debit"] - values["credit"]
    return dict(totals)


__all__ = ["trial_balance"]
