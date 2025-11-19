from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # boto3 is optional in local dev / CI
    import boto3  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    boto3 = None

# v0.5.11u-7: Compression support
from apps.common.compress import should_compress, gzip_bytes, gunzip_bytes

_S3_COMPRESS = os.getenv("DECISIONOS_S3_COMPRESS", "1") in ("1", "true", "yes")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _lock_path(dest: Path) -> Path:
    return Path(f"{dest}.lock.json")


def _sha256_bytes(blob: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(blob)
    return digest.hexdigest()


@dataclass
class S3Result:
    adapter: str
    bucket: str
    key: str
    url: str
    extra: Dict[str, Any]


class S3Adapter:
    def put_with_object_lock(
        self,
        bucket: str,
        key: str,
        data: bytes,
        lock_mode: str = "GOVERNANCE",
        retention_days: int = 30,
        compress: bool = False,
    ) -> S3Result:
        raise NotImplementedError

    def url_for(self, bucket: str, key: str) -> str:
        raise NotImplementedError

    def list_keys(self, bucket: str, prefix: str) -> List[str]:
        raise NotImplementedError

    def get_object(self, bucket: str, key: str) -> Dict[str, Any]:
        raise NotImplementedError


class StubS3Adapter(S3Adapter):
    """
    Minimal stub that mirrors uploads to the local filesystem.
    """

    def __init__(self, root: Optional[str] = None):
        self.root = Path(root or os.getenv("DECISIONOS_S3_STUB_ROOT", "var/s3_stub")).expanduser()

    def put_with_object_lock(
        self,
        bucket: str,
        key: str,
        data: bytes,
        lock_mode: str = "GOVERNANCE",
        retention_days: int = 30,
        compress: bool = False,
    ) -> S3Result:
        # v0.5.11u-7: Compression for JSON files
        upload_data = data
        upload_key = key
        content_encoding = None

        if compress and _S3_COMPRESS and should_compress(len(data)):
            upload_data = gzip_bytes(data)
            if not key.endswith(".gz"):
                upload_key = f"{key}.gz"
            content_encoding = "gzip"

        dest = self.root / bucket / upload_key
        _ensure_dir(dest.parent)
        dest.write_bytes(upload_data)

        retain_until = (_utcnow() + timedelta(days=retention_days)).isoformat().replace("+00:00", "Z")
        lock_payload = {
            "mode": lock_mode,
            "retention_days": retention_days,
            "retain_until": retain_until,
            "content_encoding": content_encoding,
        }
        _lock_path(dest).write_text(json.dumps(lock_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return S3Result(
            adapter="stub",
            bucket=bucket,
            key=upload_key,
            url=self.url_for(bucket, upload_key),
            extra={"retain_until": retain_until, "content_encoding": content_encoding},
        )

    def url_for(self, bucket: str, key: str) -> str:
        return f"stub://{bucket}/{key}"

    def list_keys(self, bucket: str, prefix: str) -> List[str]:
        base = self.root / bucket
        base_parent = base
        target = base / prefix if prefix else base
        if not target.exists():
            return []
        keys: List[str] = []
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if path.name.endswith(".lock.json"):
                continue
            rel = path.relative_to(base_parent)
            key = rel.as_posix()
            if prefix and not key.startswith(prefix):
                continue
            keys.append(key)
        return sorted(keys)

    def get_object(self, bucket: str, key: str) -> Dict[str, Any]:
        path = self.root / bucket / key
        data = path.read_bytes()
        lock = None
        lock_path = _lock_path(path)
        if lock_path.exists():
            lock = json.loads(lock_path.read_text(encoding="utf-8"))

        # v0.5.11u-7: Auto-decompress if gzipped
        content_encoding = (lock or {}).get("content_encoding")
        if content_encoding == "gzip" or key.endswith(".gz"):
            try:
                data = gunzip_bytes(data)
            except Exception:
                pass  # Return compressed data if decompression fails

        return {"Body": data, "ETag": _sha256_bytes(data), "Lock": lock}


class AWSS3Adapter(S3Adapter):
    """
    Thin wrapper over boto3 that applies ObjectLock headers.
    """

    def __init__(self):
        if boto3 is None:  # pragma: no cover - optional dependency
            raise RuntimeError("boto3 not available")
        self.client = boto3.client("s3")  # type: ignore[attr-defined]

    def put_with_object_lock(
        self,
        bucket: str,
        key: str,
        data: bytes,
        lock_mode: str = "GOVERNANCE",
        retention_days: int = 30,
        compress: bool = False,
    ) -> S3Result:
        # v0.5.11u-7: Compression for JSON files
        upload_data = data
        upload_key = key
        content_encoding = None
        metadata = {}

        if compress and _S3_COMPRESS and should_compress(len(data)):
            upload_data = gzip_bytes(data)
            if not key.endswith(".gz"):
                upload_key = f"{key}.gz"
            content_encoding = "gzip"
            metadata["content-encoding"] = "gzip"

        retain_until = _utcnow() + timedelta(days=retention_days)
        put_kwargs = {
            "Bucket": bucket,
            "Key": upload_key,
            "Body": io.BytesIO(upload_data),
            "ObjectLockMode": lock_mode,
            "ObjectLockRetainUntilDate": retain_until,
        }
        if content_encoding:
            put_kwargs["ContentEncoding"] = content_encoding
        if metadata:
            put_kwargs["Metadata"] = metadata

        resp = self.client.put_object(**put_kwargs)
        etag = (resp or {}).get("ETag", "").strip('"')
        version_id = (resp or {}).get("VersionId")
        return S3Result(
            adapter="aws",
            bucket=bucket,
            key=upload_key,
            url=self.url_for(bucket, upload_key),
            extra={
                "etag": etag,
                "version_id": version_id,
                "retain_until": retain_until.isoformat().replace("+00:00", "Z"),
                "content_encoding": content_encoding,
            },
        )

    def url_for(self, bucket: str, key: str) -> str:
        return f"s3://{bucket}/{key}"

    def list_keys(self, bucket: str, prefix: str) -> List[str]:
        keys: List[str] = []
        token: Optional[str] = None
        while True:
            kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = self.client.list_objects_v2(**kwargs)
            for item in resp.get("Contents", []) or []:
                key = item["Key"]
                if not key.endswith(".lock.json"):
                    keys.append(key)
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
            else:
                break
        return keys

    def get_object(self, bucket: str, key: str) -> Dict[str, Any]:
        resp = self.client.get_object(Bucket=bucket, Key=key)
        body = resp["Body"].read()
        etag = (resp.get("ETag") or "").strip('"')
        content_encoding = resp.get("ContentEncoding")

        # v0.5.11u-7: Auto-decompress if gzipped
        if content_encoding == "gzip" or key.endswith(".gz"):
            try:
                body = gunzip_bytes(body)
            except Exception:
                pass  # Return compressed data if decompression fails

        lock = None
        try:
            head = self.client.head_object(Bucket=bucket, Key=key)
            lock_mode = head.get("ObjectLockMode")
            if lock_mode:
                retain = head.get("ObjectLockRetainUntilDate")
                retain_iso = None
                if hasattr(retain, "isoformat"):
                    retain_iso = retain.isoformat().replace("+00:00", "Z")
                lock = {"mode": lock_mode, "retain_until": retain_iso, "content_encoding": content_encoding}
        except Exception:  # pragma: no cover - best-effort
            lock = None
        return {"Body": body, "ETag": etag, "Lock": lock}


def select_adapter() -> S3Adapter:
    mode = os.getenv("DECISIONOS_S3_MODE", "stub").lower()
    if mode == "aws":
        try:
            return AWSS3Adapter()
        except Exception:
            # boto3 missing or unusable: fallback to stub for safety
            pass
    return StubS3Adapter()


__all__ = ["S3Adapter", "StubS3Adapter", "AWSS3Adapter", "select_adapter", "S3Result"]
