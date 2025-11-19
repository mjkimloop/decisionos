# tests/common/test_compress_threshold_v1.py
"""Test compression threshold and utilities (v0.5.11u-7)."""
from __future__ import annotations

from apps.common.compress import (
    should_compress,
    gzip_bytes,
    gunzip_bytes,
    negotiate_gzip,
    compress_ratio,
    bytes_saved,
)


def test_threshold_env(monkeypatch):
    """Test compression threshold respects environment variable."""
    monkeypatch.setenv("DECISIONOS_COMPRESS_MIN_BYTES", "10")
    monkeypatch.setenv("DECISIONOS_COMPRESS_ENABLE", "1")

    # Force reload module
    import importlib
    from apps.common import compress

    importlib.reload(compress)

    assert compress.should_compress(9) is False
    assert compress.should_compress(10) is True
    assert compress.should_compress(11) is True


def test_gzip_roundtrip():
    """Test gzip compression and decompression."""
    original = b"1234567890" * 100
    compressed = gzip_bytes(original, level=6)

    assert isinstance(compressed, bytes)
    assert len(compressed) < len(original)

    decompressed = gunzip_bytes(compressed)
    assert decompressed == original


def test_negotiate_gzip_variants():
    """Test Accept-Encoding negotiation."""
    assert negotiate_gzip("gzip, deflate, br") is True
    assert negotiate_gzip("gzip") is True
    assert negotiate_gzip("*") is True
    assert negotiate_gzip("GZIP") is True  # Case insensitive
    assert negotiate_gzip("identity") is False
    assert negotiate_gzip("") is False
    assert negotiate_gzip(None) is False


def test_compress_ratio_calculation():
    """Test compression ratio calculation."""
    assert compress_ratio(100, 50) == 0.5
    assert compress_ratio(100, 100) == 1.0
    assert compress_ratio(0, 0) == 1.0  # Edge case


def test_bytes_saved_calculation():
    """Test bytes saved calculation."""
    assert bytes_saved(100, 50) == 50
    assert bytes_saved(100, 100) == 0
    assert bytes_saved(100, 110) == -10  # Compression increased size
