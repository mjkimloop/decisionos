from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet
from packages.common.config import settings


def _get_cipher() -> Fernet | None:
    if settings.aes_key_b64:
        try:
            key = settings.aes_key_b64.encode("utf-8")
            return Fernet(key)
        except Exception:
            return None
    return None


def _mask_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Simple DLP masking for PII-like keys
    masked = {}
    for k, v in payload.items():
        if any(pat in k.lower() for pat in ["ssn", "phone", "email"]):
            masked[k] = "***MASKED***"
        else:
            masked[k] = v
    return masked


@dataclass
class AuditRecord:
    decision_id: str
    prev_hash: str
    curr_hash: str
    payload: Dict[str, Any]
    created_at: str


class AuditLedger:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.audit_log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cipher = _get_cipher()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        try:
            *_, last = self.path.read_text(encoding="utf-8").splitlines()
            obj = json.loads(last)
            return obj.get("curr_hash", "0" * 64)
        except Exception:
            return "0" * 64

    def append(self, decision_id: str, payload: Dict[str, Any]) -> AuditRecord:
        masked = _mask_payload(payload)
        prev_hash = self._last_hash()
        data = {
            "decision_id": decision_id,
            "payload": masked,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        body = json.dumps(data, sort_keys=True).encode("utf-8")
        if self.cipher:
            body = self.cipher.encrypt(body)
            body_repr = base64.urlsafe_b64encode(body).decode("utf-8")
        else:
            body_repr = data
        raw = json.dumps(body_repr, sort_keys=True).encode("utf-8") if isinstance(body_repr, dict) else body_repr.encode("utf-8")
        curr_hash = hashlib.sha256(prev_hash.encode("utf-8") + raw).hexdigest()

        record = {
            "decision_id": decision_id,
            "prev_hash": prev_hash,
            "curr_hash": curr_hash,
            "payload": body_repr,
            "created_at": data["created_at"],
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # In a production environment, the ledger file would be periodically
        # uploaded to a WORM (Write-Once, Read-Many) compliant storage,
        # such as an AWS S3 bucket with Object Lock enabled.
        # This ensures the immutability of the audit trail.
        # Example:
        # upload_to_worm_bucket(self.path)

        return AuditRecord(**record)
