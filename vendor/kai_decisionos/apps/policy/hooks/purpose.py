from __future__ import annotations

from typing import Dict, Iterable, Optional

from apps.consent import store as consent_store
from apps.executor.audit_verifier import get_consent_snapshot


class PurposeBindingError(Exception):
    def __init__(self, reason: str, detail: Optional[Dict] = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


def require_consent_for_subject(subject_id: str | None, purpose: str, scope: Iterable[str] | None = None) -> Dict | None:
    if not subject_id:
        raise PurposeBindingError("subject_id_required")

    allowed, snapshot = consent_store.has_active_consent(subject_id, purpose, scope=scope)
    if not allowed:
        raise PurposeBindingError("consent_required", detail={"purpose": purpose, "scope": list(scope or [])})
    return snapshot


def enforce_purpose_binding(
    subject_id: str | None,
    *,
    purpose: str,
    scope: Iterable[str] | None = None,
    require_consent: bool = True,
) -> Dict | None:
    if require_consent:
        return require_consent_for_subject(subject_id, purpose, scope)
    return None


def attach_consent_snapshot(payload: Dict, subject_id: str, purpose: str | None = None) -> None:
    snapshot = get_consent_snapshot(subject_id, purpose=purpose)
    if snapshot:
        payload["consent_snapshot"] = snapshot


__all__ = ["PurposeBindingError", "enforce_purpose_binding", "require_consent_for_subject", "attach_consent_snapshot"]
