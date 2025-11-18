"""
Gate O — Redis ETag Store Lua atomic operations tests
"""
import json
import time
import os
import pytest

pytestmark = pytest.mark.gate_o

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_put_cas_delta():
    """Test PUT, CAS, and DELTA operations"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.etag_store import ETagStore

    s = ETagStore(r)
    key = "dos:etag:test:abc"

    # Clean up
    r.delete(key)

    # PUT: unconditional insert
    assert s.put(key, {"a": 1}) == "OK"

    # Get current ETag
    h = r.hgetall(key)
    et = h[b"etag"].decode()

    # CAS with wrong ETag should fail
    assert s.cas(key, {"a": 2}, "bad") == "NOMATCH"

    # CAS with correct ETag should succeed
    assert s.cas(key, {"a": 2}, et) == "OK"

    # Get new ETag
    et2 = r.hget(key, "etag").decode()

    # DELTA with correct base ETag
    assert s.delta_put(key, {"a": 3}, base_etag=et2) == "OK"

    # Clean up
    r.delete(key)


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_cas_missing_key():
    """Test CAS on missing key returns MISSING"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.etag_store import ETagStore

    s = ETagStore(r)
    key = "dos:etag:test:missing"

    r.delete(key)

    # CAS on missing key
    assert s.cas(key, {"a": 1}, "any") == "MISSING"

    r.delete(key)


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_delta_nomatch():
    """Test DELTA with wrong base ETag returns NOMATCH"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.etag_store import ETagStore

    s = ETagStore(r)
    key = "dos:etag:test:delta"

    r.delete(key)

    # PUT initial value
    s.put(key, {"a": 1})

    # DELTA with wrong base ETag
    assert s.delta_put(key, {"a": 2}, base_etag="wrong") == "NOMATCH"

    r.delete(key)


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_ttl_applied():
    """Test that TTL is correctly applied"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.etag_store import ETagStore

    s = ETagStore(r, ttl_ms=1000)  # 1 second TTL
    key = "dos:etag:test:ttl"

    r.delete(key)

    # PUT with TTL
    s.put(key, {"a": 1})

    # Check TTL is set (in milliseconds)
    ttl = r.pttl(key)
    assert 0 < ttl <= 1000

    r.delete(key)
