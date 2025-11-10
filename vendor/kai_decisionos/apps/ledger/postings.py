from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class Posting:
    id: str
    ts: str
    account: str
    debit: int
    credit: int
    currency: str
    ref: Optional[str] = None
    meta: Dict[str, object] = field(default_factory=dict)


POSTINGS: List[Posting] = []


def post_entry(account: str, *, debit: int = 0, credit: int = 0, currency: str = "KRW", ref: str | None = None, meta: dict | None = None) -> Posting:
    if debit and credit:
        raise ValueError("entry_must_be_single_sided")
    if debit < 0 or credit < 0:
        raise ValueError("amount_negative")
    entry = Posting(
        id=f"lg_{uuid4().hex[:12]}",
        ts=datetime.now(timezone.utc).isoformat(),
        account=account,
        debit=debit,
        credit=credit,
        currency=currency,
        ref=ref,
        meta=meta or {},
    )
    POSTINGS.append(entry)
    return entry


def post_double_entry(entries: List[dict]) -> List[Posting]:
    total_debit = sum(e.get("debit", 0) for e in entries)
    total_credit = sum(e.get("credit", 0) for e in entries)
    if total_debit != total_credit:
        raise ValueError("debits_must_equal_credits")
    result = []
    for entry in entries:
        result.append(
            post_entry(
                entry["account"],
                debit=entry.get("debit", 0),
                credit=entry.get("credit", 0),
                currency=entry.get("currency", "KRW"),
                ref=entry.get("ref"),
                meta=entry.get("meta"),
            )
        )
    return result


def list_postings(account: str | None = None) -> List[Posting]:
    if account:
        return [p for p in POSTINGS if p.account == account]
    return list(POSTINGS)


def clear_postings() -> None:
    POSTINGS.clear()


__all__ = ["Posting", "post_entry", "post_double_entry", "list_postings", "clear_postings", "POSTINGS"]
