from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConsentRecord:
    id: str
    subject_id: str
    doc_hash: str
    purpose: str
    scope: List[str] = field(default_factory=list)
    granted_at: str = field(default_factory=_now)
    revoked_at: Optional[str] = None
    meta: Dict[str, object] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.revoked_at is None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["active"] = self.active
        return payload


_CONSENTS: Dict[str, List[ConsentRecord]] = {}


def grant(subject_id: str, doc_hash: str, purpose: str, scope: Optional[Iterable[str]] = None, meta: Optional[Dict] = None) -> Dict:
    if not purpose:
        raise ValueError("purpose_required")
    record = ConsentRecord(
        id=str(uuid.uuid4()),
        subject_id=subject_id,
        doc_hash=doc_hash,
        purpose=purpose,
        scope=[str(item) for item in (scope or [])],
        granted_at=_now(),
        meta=meta or {},
    )
    _CONSENTS.setdefault(subject_id, []).append(record)
    return record.to_dict()


def revoke(subject_id: str, doc_hash: str, purpose: Optional[str] = None) -> Optional[Dict]:
    for rec in reversed(_CONSENTS.get(subject_id, [])):
        if rec.doc_hash == doc_hash and (purpose is None or rec.purpose == purpose) and rec.active:
            rec.revoked_at = _now()
            return rec.to_dict()
    return None


def list_by_subject(subject_id: str, purpose: Optional[str] = None) -> List[Dict]:
    items = _CONSENTS.get(subject_id, [])
    if purpose:
        items = [rec for rec in items if rec.purpose == purpose]
    return [rec.to_dict() for rec in items]


def latest_snapshot(subject_id: str, purpose: Optional[str] = None) -> Optional[Dict]:
    items = _CONSENTS.get(subject_id, [])
    if purpose:
        items = [rec for rec in items if rec.purpose == purpose]
    if not items:
        return None
    return items[-1].to_dict()


def has_active_consent(subject_id: str, purpose: str, scope: Optional[Iterable[str]] = None) -> Tuple[bool, Optional[Dict]]:
    scope_set = set(scope or [])
    for rec in reversed(_CONSENTS.get(subject_id, [])):
        if rec.purpose != purpose:
            continue
        if not rec.active:
            continue
        if scope_set and not scope_set.issubset(set(rec.scope)):
            continue
        return True, rec.to_dict()
    return False, None


def clear() -> None:
    _CONSENTS.clear()


__all__ = [
    "ConsentRecord",
    "grant",
    "revoke",
    "list_by_subject",
    "latest_snapshot",
    "has_active_consent",
    "clear",
]
