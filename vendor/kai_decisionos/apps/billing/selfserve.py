from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from apps.tenancy.models import ORGS
from apps.tenancy.entitlements import set_plan_for_org


SUBSCRIPTIONS: Dict[str, dict] = {}


def subscribe(org_id: str, plan: str, effective_at: Optional[str] = None) -> dict:
    org = ORGS.get(org_id)
    if not org:
        raise KeyError("org_not_found")
    set_plan_for_org(org_id, plan)
    record = {
        "org_id": org_id,
        "plan": plan,
        "effective_at": effective_at or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    SUBSCRIPTIONS[org_id] = record
    return record


def get_subscription(org_id: str) -> Optional[dict]:
    return SUBSCRIPTIONS.get(org_id)


def list_subscriptions() -> Dict[str, dict]:
    return SUBSCRIPTIONS


__all__ = ["subscribe", "get_subscription", "list_subscriptions", "SUBSCRIPTIONS"]

