# tests/s3/test_stub_upload_gzip_v1.py
"""Test S3 stub adapter gzip compression (v0.5.11u-7)."""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

from apps.common.s3_adapter import StubS3Adapter


def test_stub_upload_with_compression(tmp_path, monkeypatch):
    """
    Test S3 stub adapter compresses JSON uploads.

    Acceptance criteria:
    1. compress=True flag enables compression
    2. .gz extension added to key automatically
    3. File is actually gzipped on disk
    4. Lock metadata includes content_encoding=gzip
    5. Decompression works correctly
    """
    monkeypatch.setenv("DECISIONOS_S3_COMPRESS", "1")
    monkeypatch.setenv("DECISIONOS_COMPRESS_MIN_BYTES", "100")  # Lower threshold

    # Force reload modules to pick up env vars
    import importlib
    from apps.common import compress, s3_adapter

    importlib.reload(compress)
    importlib.reload(s3_adapter)

    adapter = s3_adapter.StubS3Adapter(root=str(tmp_path))

    # Create test data (large enough to exceed threshold)
    evidence = {
        "bucket": "2025-11-19",
        "label": "PERF_DEGRADATION",
        "score": 0.95,
        "data": "x" * 200,  # Make data large enough to exceed 100 byte threshold
    }
    data = json.dumps(evidence, ensure_ascii=False).encode("utf-8")

    # Upload with compression
    result = adapter.put_with_object_lock(
        bucket="decisionos-evidence",
        key="evidence/test.json",
        data=data,
        compress=True,
    )

    # Verify key has .gz extension
    assert result.key.endswith(".gz"), f"Expected .gz extension, got {result.key}"
    assert result.key == "evidence/test.json.gz"

    # Verify content_encoding metadata
    assert result.extra["content_encoding"] == "gzip"

    # Verify file exists on disk with .gz extension
    file_path = tmp_path / "decisionos-evidence" / "evidence" / "test.json.gz"
    assert file_path.exists()

    # Verify file is actually gzipped
    compressed_data = file_path.read_bytes()
    decompressed = gzip.decompress(compressed_data)
    recovered = json.loads(decompressed.decode("utf-8"))
    assert recovered == evidence

    # Verify lock metadata
    lock_path = Path(f"{file_path}.lock.json")
    assert lock_path.exists()
    lock_data = json.loads(lock_path.read_text())
    assert lock_data["content_encoding"] == "gzip"


def test_stub_upload_without_compression(tmp_path, monkeypatch):
    """Test S3 stub adapter without compression (compress=False)."""
    monkeypatch.setenv("DECISIONOS_S3_COMPRESS", "1")

    adapter = StubS3Adapter(root=str(tmp_path))

    data = b"small data"

    result = adapter.put_with_object_lock(
        bucket="test-bucket",
        key="test.json",
        data=data,
        compress=False,  # Explicitly disable
    )

    # Verify no .gz extension
    assert result.key == "test.json"
    assert result.extra.get("content_encoding") is None

    # Verify file is NOT compressed
    file_path = tmp_path / "test-bucket" / "test.json"
    assert file_path.exists()
    assert file_path.read_bytes() == data


def test_stub_get_object_auto_decompress(tmp_path, monkeypatch):
    """Test S3 stub adapter auto-decompresses on get_object."""
    monkeypatch.setenv("DECISIONOS_S3_COMPRESS", "1")
    monkeypatch.setenv("DECISIONOS_COMPRESS_MIN_BYTES", "100")

    # Force reload modules to pick up env vars
    import importlib
    from apps.common import compress, s3_adapter

    importlib.reload(compress)
    importlib.reload(s3_adapter)

    adapter = s3_adapter.StubS3Adapter(root=str(tmp_path))

    # Upload compressed data (large enough to exceed threshold)
    evidence = {"test": "data", "padding": "x" * 200}
    data = json.dumps(evidence).encode("utf-8")

    result = adapter.put_with_object_lock(
        bucket="test-bucket",
        key="evidence/test.json",
        data=data,
        compress=True,
    )

    # Get object - should auto-decompress
    obj = adapter.get_object(bucket="test-bucket", key=result.key)

    # Body should be decompressed
    recovered = json.loads(obj["Body"].decode("utf-8"))
    assert recovered["test"] == evidence["test"]

    # Lock metadata should indicate gzip
    assert obj["Lock"]["content_encoding"] == "gzip"


def test_stub_compression_disabled_env(tmp_path, monkeypatch):
    """Test compression is disabled when DECISIONOS_S3_COMPRESS=0."""
    monkeypatch.setenv("DECISIONOS_S3_COMPRESS", "0")

    # Force reload module to pick up new env var
    import importlib
    from apps.common import s3_adapter

    importlib.reload(s3_adapter)

    adapter = s3_adapter.StubS3Adapter(root=str(tmp_path))

    data = json.dumps({"test": "data"}).encode("utf-8")

    result = adapter.put_with_object_lock(
        bucket="test-bucket",
        key="test.json",
        data=data,
        compress=True,  # Request compression
    )

    # Should NOT compress when env var is 0
    assert result.key == "test.json"
    assert result.extra.get("content_encoding") is None


def test_stub_compression_threshold(tmp_path, monkeypatch):
    """Test compression only applies to data above threshold."""
    monkeypatch.setenv("DECISIONOS_S3_COMPRESS", "1")
    monkeypatch.setenv("DECISIONOS_COMPRESS_MIN_BYTES", "1000")  # High threshold

    # Force reload modules to pick up new env var
    import importlib
    from apps.common import compress, s3_adapter

    importlib.reload(compress)
    importlib.reload(s3_adapter)

    adapter = s3_adapter.StubS3Adapter(root=str(tmp_path))

    # Small data below threshold
    small_data = b"x" * 500

    result = adapter.put_with_object_lock(
        bucket="test-bucket",
        key="small.json",
        data=small_data,
        compress=True,
    )

    # Should NOT compress (below threshold)
    assert result.key == "small.json"
    assert result.extra.get("content_encoding") is None

    # Large data above threshold
    large_data = b"x" * 1500

    result2 = adapter.put_with_object_lock(
        bucket="test-bucket",
        key="large.json",
        data=large_data,
        compress=True,
    )

    # Should compress (above threshold)
    assert result2.key == "large.json.gz"
    assert result2.extra["content_encoding"] == "gzip"
