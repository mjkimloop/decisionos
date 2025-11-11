import pytest
import json
import os
from datetime import datetime, timezone

@pytest.mark.gate_ops
def test_delta_headers_store_and_retrieve():
    """ETag 스냅샷 저장 및 조회 테스트"""
    from apps.ops.cache.etag_store import InMemoryETagStore

    store = InMemoryETagStore()
    test_etag = "W/\"test123\""
    test_payload = {"window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T02:00:00Z"}, "data": "test"}

    store.put(test_etag, test_payload, ttl_sec=60)
    retrieved = store.get(test_etag)

    assert retrieved is not None
    assert retrieved["window"]["start"] == "2025-01-01T00:00:00Z"
    assert retrieved["data"] == "test"

@pytest.mark.gate_ops
def test_delta_computation():
    """증분 계산 로직 테스트"""
    from apps.ops.cards.delta import compute_delta_summary

    prev = {
        "window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T02:00:00Z"},
        "catalog_sha": "abc123",
        "raw": {"reason:infra-latency": 10, "reason:app-error": 5},
        "buckets": [
            {"ts": "2025-01-01T00:00:00Z", "end": "2025-01-01T01:00:00Z", "count": 10},
            {"ts": "2025-01-01T01:00:00Z", "end": "2025-01-01T02:00:00Z", "count": 5},
        ]
    }

    curr = {
        "window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T02:00:00Z"},
        "catalog_sha": "abc123",
        "raw": {"reason:infra-latency": 15, "reason:app-error": 5},
        "buckets": [
            {"ts": "2025-01-01T00:00:00Z", "end": "2025-01-01T01:00:00Z", "count": 15},
            {"ts": "2025-01-01T01:00:00Z", "end": "2025-01-01T02:00:00Z", "count": 5},
            {"ts": "2025-01-01T02:00:00Z", "end": "2025-01-01T03:00:00Z", "count": 3},
        ]
    }

    delta = compute_delta_summary(prev, curr)

    assert delta["delta_mode"] == "shallow"
    assert "buckets_delta" in delta
    assert len(delta["buckets_delta"]["added"]) == 1  # 새 버킷 1개
    assert len(delta["buckets_delta"]["changed"]) == 1  # 변경된 버킷 1개

@pytest.mark.gate_ops
def test_same_window_check():
    """동일 윈도우 체크 테스트"""
    from apps.ops.cards.delta import same_window

    prev = {"window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T02:00:00Z"}}
    curr1 = {"window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T02:00:00Z"}}
    curr2 = {"window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T03:00:00Z"}}

    assert same_window(prev, curr1) is True
    assert same_window(prev, curr2) is False

@pytest.mark.gate_ops
def test_etag_store_expiration():
    """ETag 저장소 만료 테스트"""
    import time
    from apps.ops.cache.etag_store import InMemoryETagStore

    store = InMemoryETagStore()
    test_etag = "W/\"expire-test\""
    test_payload = {"data": "should-expire"}

    # TTL 1초로 저장
    store.put(test_etag, test_payload, ttl_sec=1)
    assert store.get(test_etag) is not None

    # 1.5초 대기 후 만료 확인
    time.sleep(1.5)
    assert store.get(test_etag) is None
