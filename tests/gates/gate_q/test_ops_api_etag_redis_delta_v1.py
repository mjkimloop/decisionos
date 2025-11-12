"""
Test Ops API ETag + Redis + Delta (gate_q)
"""
import pytest
import time
from apps.ops.cache.etag_store import (
    InMemoryETagStore,
    RedisETagStore,
    build_etag_store,
)


@pytest.mark.gate_q
def test_inmemory_put_get():
    """Test InMemory store basic put/get"""
    store = InMemoryETagStore(default_ttl=60)

    snapshot = {"data": "test", "value": 123}
    store.put("test-etag", snapshot, ttl_sec=10)

    result = store.get("test-etag")
    assert result == snapshot


@pytest.mark.gate_q
def test_inmemory_ttl_expiration():
    """Test InMemory store TTL expiration"""
    store = InMemoryETagStore(default_ttl=1)

    snapshot = {"data": "expires"}
    store.put("expire-test", snapshot, ttl_sec=1)

    # Should exist immediately
    assert store.get("expire-test") == snapshot

    # Wait for expiration
    time.sleep(1.1)

    # Should be gone
    assert store.get("expire-test") is None


@pytest.mark.gate_q
def test_inmemory_invalidate():
    """Test InMemory store invalidation"""
    store = InMemoryETagStore()

    store.put("key1", {"data": 1})
    store.put("key2", {"data": 2})
    store.put("other", {"data": 3})

    # Invalidate keys starting with "key"
    count = store.invalidate("key")

    assert count == 2
    assert store.get("key1") is None
    assert store.get("key2") is None
    assert store.get("other") == {"data": 3}  # Not invalidated


@pytest.mark.gate_q
def test_inmemory_stats():
    """Test InMemory store statistics"""
    store = InMemoryETagStore()

    store.put("key1", {"data": 1})
    store.put("key2", {"data": 2})

    stats = store.stats()

    assert stats["backend"] == "memory"
    assert stats["total_keys"] == 2


@pytest.mark.gate_q
def test_build_etag_store_default(monkeypatch):
    """Test build_etag_store returns InMemory by default"""
    monkeypatch.delenv("DECISIONOS_ETAG_BACKEND", raising=False)

    store = build_etag_store()

    assert isinstance(store, InMemoryETagStore)


@pytest.mark.gate_q
def test_build_etag_store_memory_explicit(monkeypatch):
    """Test build_etag_store with explicit memory backend"""
    monkeypatch.setenv("DECISIONOS_ETAG_BACKEND", "memory")

    store = build_etag_store()

    assert isinstance(store, InMemoryETagStore)


@pytest.mark.gate_q
def test_build_etag_store_redis_fallback(monkeypatch):
    """Test build_etag_store falls back to InMemory on Redis failure"""
    monkeypatch.setenv("DECISIONOS_ETAG_BACKEND", "redis")
    monkeypatch.setenv("DECISIONOS_REDIS_URL", "redis://nonexistent:6379/0")

    # Should fallback to InMemory if Redis unavailable
    store = build_etag_store()

    # Minimum requirement: store should work
    store.put("test", {"data": 1})
    assert store.get("test") == {"data": 1}


@pytest.mark.gate_q
def test_build_etag_store_custom_ttl(monkeypatch):
    """Test build_etag_store respects custom TTL"""
    monkeypatch.setenv("DECISIONOS_ETAG_TTL", "120")

    store = build_etag_store()

    assert store.default_ttl == 120


@pytest.mark.gate_q
def test_inmemory_overwrite():
    """Test InMemory store overwrites existing ETag"""
    store = InMemoryETagStore()

    store.put("key", {"version": 1})
    assert store.get("key") == {"version": 1}

    store.put("key", {"version": 2})
    assert store.get("key") == {"version": 2}


@pytest.mark.gate_q
def test_inmemory_different_etags():
    """Test InMemory store handles different ETags independently"""
    store = InMemoryETagStore()

    store.put("etag1", {"data": "A"})
    store.put("etag2", {"data": "B"})

    assert store.get("etag1") == {"data": "A"}
    assert store.get("etag2") == {"data": "B"}


@pytest.mark.gate_q
def test_inmemory_stats_evicts_expired():
    """Test stats() evicts expired entries"""
    store = InMemoryETagStore()

    store.put("active", {"data": 1}, ttl_sec=60)
    store.put("expired", {"data": 2}, ttl_sec=1)

    # Wait for expiration
    time.sleep(1.1)

    stats = store.stats()

    # stats() should evict expired entries
    assert stats["total_keys"] == 1
    assert store.get("active") == {"data": 1}
    assert store.get("expired") is None


@pytest.mark.gate_q
def test_inmemory_invalidate_no_match():
    """Test invalidate with no matching keys"""
    store = InMemoryETagStore()

    store.put("key1", {"data": 1})

    count = store.invalidate("nonexistent")

    assert count == 0
    assert store.get("key1") == {"data": 1}


@pytest.mark.gate_q
def test_delta_scenario():
    """Test Delta use case: store base snapshot, compute delta"""
    store = InMemoryETagStore()

    # Base snapshot
    base_etag = "base-123"
    base_snapshot = {
        "items": [
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
        ],
        "total": 30
    }
    store.put(base_etag, base_snapshot)

    # New snapshot
    new_etag = "new-456"
    new_snapshot = {
        "items": [
            {"id": 1, "value": 10},  # Unchanged
            {"id": 2, "value": 25},  # Changed
            {"id": 3, "value": 15},  # New
        ],
        "total": 50
    }
    store.put(new_etag, new_snapshot)

    # Retrieve both for delta computation (in real code, done in API)
    base = store.get(base_etag)
    new = store.get(new_etag)

    assert base is not None
    assert new is not None

    # Simple delta: items that changed
    delta_items = [item for item in new["items"] if item not in base["items"]]
    assert len(delta_items) == 2  # id=2 (changed) and id=3 (new)


@pytest.mark.gate_q
def test_build_etag_store_no_redis_url(monkeypatch):
    """Test Redis backend without URL falls back to InMemory"""
    monkeypatch.setenv("DECISIONOS_ETAG_BACKEND", "redis")
    monkeypatch.delenv("DECISIONOS_REDIS_URL", raising=False)

    store = build_etag_store()

    assert isinstance(store, InMemoryETagStore)
