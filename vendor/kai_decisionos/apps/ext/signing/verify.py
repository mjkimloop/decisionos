from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path

from .sign import DEFAULT_SECRET


def verify_signature(artifact_path: Path, signature: str, secret: bytes | None = None) -> bool:
    secret = secret or DEFAULT_SECRET
    expected = base64.urlsafe_b64decode(signature + "==")
    digest = hmac.new(secret, artifact_path.read_bytes(), hashlib.sha256).digest()
    return hmac.compare_digest(digest, expected)


__all__ = ["verify_signature"]
