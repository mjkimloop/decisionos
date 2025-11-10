from __future__ import annotations

from apps.dunning.engine import ENGINE
from apps.dunning.notifiers import send_notification


def mark_overdue(invoice_id: str, reason: str = "unpaid", org_id: str | None = None) -> dict:
    record = ENGINE.start(invoice_id=invoice_id, org_id=org_id, reason=reason)
    send_notification(invoice_id, "email", {"reason": reason})
    return record.as_dict()


def schedule_followup(invoice_id: str, channel: str, eta: str) -> dict:
    record = ENGINE.schedule(invoice_id, channel, eta)
    send_notification(invoice_id, channel, {"eta": eta})
    return record.as_dict()


def get_status(invoice_id: str) -> dict | None:
    return ENGINE.get(invoice_id)


__all__ = ["mark_overdue", "schedule_followup", "get_status"]
