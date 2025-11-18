from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

class S3ClientStub:
    def __init__(self):
        self.base = Path(os.getenv("DECISIONOS_S3_STUB_DIR", "var/s3"))

    def put_object(
        self,
        Bucket: str,
        Key: str,
        Body,
        ObjectLockMode: str | None = None,
        ObjectLockRetainUntilDate: str | None = None,
    ):
        data = Body if isinstance(Body, (bytes, bytearray)) else str(Body).encode()
        dest = self.base / Bucket / Key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {
            "ObjectLockMode": ObjectLockMode or "COMPLIANCE",
            "RetainUntilDate": ObjectLockRetainUntilDate
            or (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        }


def get_s3(mode: str | None = None):
    mode = mode or os.getenv("DECISIONOS_S3_MODE", "stub")
    if mode == "stub":
        return S3ClientStub()
    import boto3  # pragma: no cover

    return boto3.client("s3")
