from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone


INVOICES: dict[str, dict] = {}


def close_month(org_id: str, yyyymm: str, lines: list[dict]):
    subtotal = round(sum(l.get("amount", 0.0) for l in lines), 4)
    tax = round(subtotal * 0.1, 4)  # dev: 10%
    total = round(subtotal + tax, 4)
    inv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    invoice = {
        "id": inv_id,
        "org_id": org_id,
        "period": yyyymm,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "status": "issued",
        "created_at": now.isoformat(),
        "due_at": (now + timedelta(days=30)).isoformat(),
        "balance_due": total,
        "lines": lines,
    }
    INVOICES[inv_id] = invoice
    return invoice
