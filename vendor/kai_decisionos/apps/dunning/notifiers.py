from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List


_LOG: List[dict] = []


def send_notification(invoice_id: str, channel: str, payload: dict | None = None) -> dict:
    record = {
        "invoice_id": invoice_id,
        "channel": channel,
        "payload": payload or {},
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    _LOG.append(record)
    return record


def sent_notifications() -> List[dict]:
    return list(_LOG)


def clear_notifications() -> None:
    _LOG.clear()


__all__ = ["send_notification", "sent_notifications", "clear_notifications"]
