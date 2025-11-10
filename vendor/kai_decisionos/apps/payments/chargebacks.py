from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from apps.common.idempotency import GLOBAL_IDEMPOTENCY_STORE

_CHARGEBACKS: Dict[str, dict] = {}


def upsert_chargeback(
    *,
    idempotency_key: str,
    psp_ref: str,
    stage: str,
    amount: int,
    currency: str,
    reason: str | None,
    evidence_url: str | None,
) -> dict:
    key = f"chargeback:{idempotency_key}"
    cached = GLOBAL_IDEMPOTENCY_STORE.get(key)
    if cached:
        return cached.response
    record = {
        "psp_ref": psp_ref,
        "stage": stage,
        "amount": amount,
        "currency": currency,
        "reason": reason,
        "evidence_url": evidence_url,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _CHARGEBACKS[psp_ref] = record
    GLOBAL_IDEMPOTENCY_STORE.set(key, record)
    return record


def list_chargebacks() -> List[dict]:
    return list(_CHARGEBACKS.values())


__all__ = ["upsert_chargeback", "list_chargebacks"]
