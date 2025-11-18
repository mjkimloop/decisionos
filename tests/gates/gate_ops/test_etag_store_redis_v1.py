"""
Gate OPS — Redis ETag Store v2 tests
"""
import time
import pytest

# Check if redis is available
try:
    import redis
    from apps.ops.etag_store_redis import RedisETagStoreV2, build_etag_store_v2
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_put_and_get():
    """Test basic put and get operations"""
    import os
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")
    if not redis_url:
        pytest.skip("DECISIONOS_REDIS_URL not set")
    
    store = RedisETagStoreV2(redis_url, default_ttl=10, namespace="test:etag:")
    
    try:
        snapshot = {"data": [1, 2, 3], "meta": {"version": "v1"}}
        etag = "abc123"
        
        store.put(etag, snapshot)
        retrieved = store.get(etag)
        
        assert retrieved is not None
        assert retrieved["data"] == [1, 2, 3]
        assert retrieved["meta"]["version"] == "v1"
    finally:
        store.invalidate("*")
        store.close()

@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_ttl_expiration():
    """Test TTL expiration"""
    import os
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")
    if not redis_url:
        pytest.skip("DECISIONOS_REDIS_URL not set")
    
    store = RedisETagStoreV2(redis_url, default_ttl=1, namespace="test:etag:")
    
    try:
        snapshot = {"expires": "soon"}
        etag = "expire-test"
        
        store.put(etag, snapshot, ttl_sec=1)
        assert store.get(etag) is not None
        
        # Wait for expiration
        time.sleep(1.1)
        assert store.get(etag) is None
    finally:
        store.close()

@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_exists_and_ttl():
    """Test exists and ttl methods"""
    import os
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")
    if not redis_url:
        pytest.skip("DECISIONOS_REDIS_URL not set")
    
    store = RedisETagStoreV2(redis_url, default_ttl=10, namespace="test:etag:")
    
    try:
        etag = "exists-test"
        store.put(etag, {"data": "test"}, ttl_sec=10)
        
        assert store.exists(etag)
        
        ttl = store.ttl(etag)
        assert 0 < ttl <= 10
        
        # Non-existent key
        assert not store.exists("nonexistent")
        assert store.ttl("nonexistent") == -2
    finally:
        store.invalidate("*")
        store.close()

@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_invalidate_pattern():
    """Test pattern-based invalidation"""
    import os
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")
    if not redis_url:
        pytest.skip("DECISIONOS_REDIS_URL not set")
    
    store = RedisETagStoreV2(redis_url, default_ttl=10, namespace="test:etag:")
    
    try:
        # Put multiple entries
        store.put("user:123", {"name": "alice"})
        store.put("user:456", {"name": "bob"})
        store.put("session:789", {"token": "xyz"})
        
        # Invalidate user:* pattern
        count = store.invalidate("user:*")
        assert count == 2
        
        # User entries should be gone
        assert store.get("user:123") is None
        assert store.get("user:456") is None
        
        # Session entry should still exist
        assert store.get("session:789") is not None
    finally:
        store.invalidate("*")
        store.close()

@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_mutate():
    """Test mutate (alias for put)"""
    import os
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")
    if not redis_url:
        pytest.skip("DECISIONOS_REDIS_URL not set")
    
    store = RedisETagStoreV2(redis_url, default_ttl=10, namespace="test:etag:")
    
    try:
        etag = "mutate-test"
        store.put(etag, {"version": 1})
        
        assert store.get(etag)["version"] == 1
        
        # Mutate
        store.mutate(etag, {"version": 2})
        assert store.get(etag)["version"] == 2
    finally:
        store.invalidate("*")
        store.close()

def test_fallback_to_inmemory():
    """Test fallback to in-memory when Redis not available"""
    import os
    
    # Clear Redis URL
    old_url = os.environ.get("DECISIONOS_REDIS_URL")
    if old_url:
        del os.environ["DECISIONOS_REDIS_URL"]
    
    try:
        store = build_etag_store_v2(default_ttl=10)
        
        # Should be in-memory store
        from apps.ops.cache.etag_store import InMemoryETagStore
        assert isinstance(store, InMemoryETagStore)
        
        # Test basic functionality
        store.put("test", {"data": "value"})
        assert store.get("test")["data"] == "value"
    finally:
        if old_url:
            os.environ["DECISIONOS_REDIS_URL"] = old_url

@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_namespace_isolation():
    """Test namespace prevents key collision"""
    import os
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")
    if not redis_url:
        pytest.skip("DECISIONOS_REDIS_URL not set")
    
    store1 = RedisETagStoreV2(redis_url, default_ttl=10, namespace="ns1:")
    store2 = RedisETagStoreV2(redis_url, default_ttl=10, namespace="ns2:")
    
    try:
        # Same ETag, different namespaces
        store1.put("key", {"ns": 1})
        store2.put("key", {"ns": 2})
        
        assert store1.get("key")["ns"] == 1
        assert store2.get("key")["ns"] == 2
    finally:
        store1.invalidate("*")
        store2.invalidate("*")
        store1.close()
        store2.close()
