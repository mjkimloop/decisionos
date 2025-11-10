from __future__ import annotations

from sqlalchemy import insert

from apps.db.base import get_session
from apps.db.models import AuditLedger


def append_audit_pg(decision_id: str, prev_hash: str, curr_hash: str, payload: dict, created_at: str):
    with get_session() as s:
        s.execute(
            insert(AuditLedger).values(
                decision_id=decision_id,
                prev_hash=prev_hash,
                curr_hash=curr_hash,
                payload=payload,
                created_at=created_at,
            )
        )
        s.commit()

