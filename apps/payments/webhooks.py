from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .adapters.registry import get_adapter
from .state_machine import PaymentState, RefundState


@dataclass
class WebhookEvent:
    adapter: str
    event_type: str
    data: dict
    idempotency_key: str


class WebhookProcessor:
    def __init__(self) -> None:
        self._seen: Dict[str, str] = {}

    def parse(self, adapter_name: str, headers: dict, payload: bytes) -> WebhookEvent:
        adapter = get_adapter(adapter_name)
        event = adapter.verify_webhook(headers, payload)
        key = event.get("idempotency_key") or event.get("id")
        if not key:
            raise ValueError("missing_idempotency_key")
        event_type = event.get("type", "unknown")
        self._seen.setdefault(key, adapter_name)
        return WebhookEvent(adapter=adapter_name, event_type=event_type, data=event, idempotency_key=key)

    def is_duplicate(self, event: WebhookEvent) -> bool:
        return self._seen.get(event.idempotency_key) == event.adapter


def map_event_to_state(event_type: str) -> Tuple[PaymentState | None, RefundState | None]:
    mapping = {
        "payment_succeeded": (PaymentState.SETTLED, None),
        "payment_failed": (PaymentState.FAILED, None),
        "refund_succeeded": (None, RefundState.REFUNDED),
        "refund_failed": (None, RefundState.FAILED),
    }
    return mapping.get(event_type, (None, None))


__all__ = ["WebhookProcessor", "WebhookEvent", "map_event_to_state"]
