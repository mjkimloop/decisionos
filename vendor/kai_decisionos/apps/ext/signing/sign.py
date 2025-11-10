from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path

DEFAULT_SECRET = b"ext-dev-secret"


def sign_artifact(artifact_path: Path, secret: bytes | None = None) -> str:
    secret = secret or DEFAULT_SECRET
    digest = hmac.new(secret, artifact_path.read_bytes(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


__all__ = ["sign_artifact", "DEFAULT_SECRET"]
