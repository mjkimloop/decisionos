from __future__ import annotations

from pathlib import Path
from typing import Optional

from apps.audit_ledger.verify_hashes import verify_chain
from apps.consent.store import latest_snapshot, has_active_consent
from packages.common.config import settings


def verify_audit_chain() -> bool:
    p = Path(settings.audit_log_path)
    return bool(verify_chain(p))


def get_consent_snapshot(subject_id: str, purpose: str | None = None) -> Optional[dict]:
    return latest_snapshot(subject_id, purpose=purpose)


def ensure_consent(subject_id: str, purpose: str, scope: list[str] | None = None) -> bool:
    has_consent, _ = has_active_consent(subject_id, purpose, scope=scope)
    return has_consent
