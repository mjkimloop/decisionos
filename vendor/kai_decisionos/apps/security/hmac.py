from __future__ import annotations

import hmac
import hashlib


def verify_hmac_sha256(secret: str, body: bytes, signature_hex: str) -> bool:
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(mac, signature_hex)
    except Exception:
        return False
