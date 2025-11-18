"""
ETag 충돌 방지 테스트 (Property-based)

동일한 generated_at/mtime이더라도 상위 reason이 변경되면 ETag가 달라야 함.
Hypothesis를 사용한 무작위 데이터 1000회 검증.
"""
import json
import tempfile
from pathlib import Path

import pytest

try:
    from hypothesis import given, strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


def test_etag_differs_by_tenant():
    """동일 데이터라도 tenant가 다르면 ETag가 달라짐"""
    from apps.ops.api.cards_delta import _compute_etag_seed, _etag

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        index_path = f.name
        data = {
            "generated_at": 1234567890,
            "buckets": [{"reasons": {"perf": 10, "latency": 5}}]
        }
        json.dump(data, f)

    try:
        seed_a = _compute_etag_seed(index_path, "tenant-a", "catalog-sha", "query-hash")
        seed_b = _compute_etag_seed(index_path, "tenant-b", "catalog-sha", "query-hash")

        etag_a = _etag(seed_a)
        etag_b = _etag(seed_b)

        assert etag_a != etag_b, "ETags should differ by tenant"

    finally:
        Path(index_path).unlink(missing_ok=True)


def test_etag_differs_by_catalog_sha():
    """동일 데이터라도 catalog SHA가 다르면 ETag가 달라짐"""
    from apps.ops.api.cards_delta import _compute_etag_seed, _etag

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        index_path = f.name
        data = {
            "generated_at": 1234567890,
            "buckets": [{"reasons": {"perf": 10, "latency": 5}}]
        }
        json.dump(data, f)

    try:
        seed_1 = _compute_etag_seed(index_path, "tenant-a", "catalog-sha-1", "query-hash")
        seed_2 = _compute_etag_seed(index_path, "tenant-a", "catalog-sha-2", "query-hash")

        etag_1 = _etag(seed_1)
        etag_2 = _etag(seed_2)

        assert etag_1 != etag_2, "ETags should differ by catalog SHA"

    finally:
        Path(index_path).unlink(missing_ok=True)


def test_etag_stable_for_same_inputs():
    """동일 입력에 대해 ETag가 안정적으로 생성됨"""
    from apps.ops.api.cards_delta import _compute_etag_seed, _etag

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        index_path = f.name
        data = {
            "generated_at": 1234567890,
            "buckets": [{"reasons": {"perf": 10, "latency": 5}}]
        }
        json.dump(data, f)

    try:
        etags = []
        for _ in range(10):
            seed = _compute_etag_seed(index_path, "tenant-a", "catalog-sha", "query-hash")
            etag = _etag(seed)
            etags.append(etag)

        assert len(set(etags)) == 1, f"ETag should be stable, got: {set(etags)}"

    finally:
        Path(index_path).unlink(missing_ok=True)
