from __future__ import annotations

import hashlib
import hmac
import time


def verify_webhook(headers: dict, payload: bytes, secret: str) -> None:
    signature = headers.get("X-Ext-Signature")
    timestamp = headers.get("X-Ext-Timestamp")
    if not signature or not timestamp:
        raise ValueError("missing_headers")
    if abs(time.time() - int(timestamp)) > 300:
        raise ValueError("timestamp_out_of_range")
    expected = hmac.new(secret.encode("utf-8"), msg=(timestamp + "." + payload.decode("utf-8")).encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("invalid_signature")


__all__ = ["verify_webhook"]
