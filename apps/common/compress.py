# apps/common/compress.py
"""
Compression utilities for response and storage optimization.

Features (v0.5.11u-7):
- Threshold-based compression (DECISIONOS_COMPRESS_MIN_BYTES)
- gzip encoding with configurable level
- Accept-Encoding negotiation
- Metrics tracking (bytes saved)
"""
from __future__ import annotations

import gzip
import io
import os
import logging
from typing import Tuple

log = logging.getLogger(__name__)

# Configuration
_COMPRESS_ENABLE = os.getenv("DECISIONOS_COMPRESS_ENABLE", "1") in ("1", "true", "yes")
_MIN_BYTES = int(os.getenv("DECISIONOS_COMPRESS_MIN_BYTES", "4096"))
_GZIP_LEVEL = int(os.getenv("DECISIONOS_GZIP_LEVEL", "6"))


def should_compress(length: int) -> bool:
    """
    Check if data should be compressed based on size threshold.

    Args:
        length: Data length in bytes

    Returns:
        True if compression enabled and length >= threshold
    """
    return _COMPRESS_ENABLE and length >= _MIN_BYTES


def gzip_bytes(data: bytes, level: int = None) -> bytes:
    """
    Compress data using gzip.

    Args:
        data: Raw bytes to compress
        level: Compression level (1-9, default from env)

    Returns:
        Compressed bytes
    """
    if level is None:
        level = _GZIP_LEVEL

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=level) as f:
        f.write(data)

    compressed = buf.getvalue()

    # Metrics: bytes saved
    saved = len(data) - len(compressed)
    ratio = len(compressed) / len(data) if len(data) > 0 else 1.0

    log.debug(
        "gzip_compress",
        extra={
            "original_bytes": len(data),
            "compressed_bytes": len(compressed),
            "saved_bytes": saved,
            "ratio": f"{ratio:.2%}",
            "level": level,
        },
    )

    return compressed


def gunzip_bytes(data: bytes) -> bytes:
    """
    Decompress gzip data.

    Args:
        data: Compressed bytes

    Returns:
        Decompressed bytes
    """
    buf = io.BytesIO(data)
    with gzip.GzipFile(fileobj=buf, mode="rb") as f:
        return f.read()


def negotiate_gzip(accept_encoding: str) -> bool:
    """
    Check if client accepts gzip encoding.

    Args:
        accept_encoding: Accept-Encoding header value

    Returns:
        True if gzip is acceptable

    Examples:
        >>> negotiate_gzip("gzip, deflate, br")
        True
        >>> negotiate_gzip("identity")
        False
        >>> negotiate_gzip("*")
        True
    """
    if not accept_encoding:
        return False

    ae = accept_encoding.lower()
    return "gzip" in ae or "*" in ae


def compress_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio.

    Args:
        original_size: Original data size
        compressed_size: Compressed data size

    Returns:
        Ratio (compressed / original), 1.0 if original_size is 0
    """
    if original_size == 0:
        return 1.0
    return compressed_size / original_size


def bytes_saved(original_size: int, compressed_size: int) -> int:
    """
    Calculate bytes saved by compression.

    Args:
        original_size: Original data size
        compressed_size: Compressed data size

    Returns:
        Bytes saved (can be negative if compression increases size)
    """
    return original_size - compressed_size
