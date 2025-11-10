from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import List

from .models import (
    SignupRequest,
    SignupRecord,
    BootstrapRequest,
    BootstrapResult,
)


DEFAULT_STORE = Path("var/onboarding")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _store_path(name: str) -> Path:
    path = DEFAULT_STORE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def register_signup(request: SignupRequest) -> SignupRecord:
    record = SignupRecord(
        id=secrets.token_hex(8),
        email=request.email,
        company=request.company,
        plan=request.plan,
        notes=request.notes,
        created_at=_utcnow(),
    )
    file_path = _store_path("signups.jsonl")
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(record.model_dump_json() + "\n")
    return record


def list_signups() -> List[SignupRecord]:
    file_path = _store_path("signups.jsonl")
    if not file_path.exists():
        return []
    records: List[SignupRecord] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        records.append(SignupRecord.model_validate(data))
    return records


def bootstrap_tenant(request: BootstrapRequest) -> BootstrapResult:
    result = BootstrapResult(
        org_id=f"org-{request.signup_id[:6]}",
        project_id=f"proj-{secrets.token_hex(3)}",
        api_key=secrets.token_urlsafe(16),
    )
    file_path = _store_path("bootstrap.jsonl")
    entry = {
        "signup_id": request.signup_id,
        "org_name": request.org_name,
        "project_name": request.project_name,
        "region": request.region,
        "result": result.model_dump(),
        "created_at": _utcnow().isoformat(),
    }
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return result


def get_status_summary() -> dict[str, object]:
    return {
        "uptime": "99.95%",
        "incidents": [],
        "last_update": _utcnow().isoformat(),
    }


def get_support_contacts() -> dict[str, object]:
    return {
        "email": "support@decisionos.dev",
        "slack": "https://decisionos.slack.com/support",
        "kb": "https://docs.decisionos.dev/kb",
        "last_update": _utcnow().isoformat(),
    }


def get_pricing_catalog() -> dict[str, object]:
    return {
        "plans": [
            {"name": "trial", "price": 0, "quota": "decisions 500/mo"},
            {"name": "growth", "price": 299, "quota": "decisions 10k/mo"},
            {"name": "enterprise", "price": "custom", "quota": "negotiated"},
        ],
        "currency": "USD",
        "last_update": _utcnow().isoformat(),
    }


__all__ = [
    "register_signup",
    "list_signups",
    "bootstrap_tenant",
    "get_status_summary",
    "get_support_contacts",
    "get_pricing_catalog",
    "DEFAULT_STORE",
]
