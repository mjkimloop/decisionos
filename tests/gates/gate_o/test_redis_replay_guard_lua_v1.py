"""
Gate O — Redis Replay Guard Lua atomic operations tests
"""
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
def test_replay_guard_once():
    """Test that replay guard allows first use and rejects second"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.replay_store_redis import ReplayGuard

    g = ReplayGuard(r, window_ms=10000)
    now = int(time.time() * 1000)

    # First use: should be allowed
    res = g.allow_once("t1", "nonce1", now)
    assert res == "ALLOW"

    # Second use: should be rejected
    res2 = g.allow_once("t1", "nonce1", now)
    assert res2 == "REJECT_EXIST"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_replay_guard_clock_skew():
    """Test that clock skew outside window is rejected"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.replay_store_redis import ReplayGuard

    g = ReplayGuard(r, window_ms=10000)

    # Timestamp from far future (beyond skew window)
    far_future = int(time.time() * 1000) + 120000  # 2 minutes ahead

    res = g.allow_once("t2", "nonce2", far_future, skew_ms=60000)
    assert res == "REJECT_CLOCKSKEW"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_replay_guard_different_tenants():
    """Test that different tenants can use same nonce"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.replay_store_redis import ReplayGuard

    g = ReplayGuard(r, window_ms=10000)
    now = int(time.time() * 1000)

    # Tenant 1 uses nonce
    res1 = g.allow_once("tenant1", "shared_nonce", now)
    assert res1 == "ALLOW"

    # Tenant 2 can use same nonce
    res2 = g.allow_once("tenant2", "shared_nonce", now)
    assert res2 == "ALLOW"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_replay_guard_ttl_expiration():
    """Test that nonce expires after window"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")

    from apps.storage.replay_store_redis import ReplayGuard

    g = ReplayGuard(r, window_ms=500)  # 500ms window
    now = int(time.time() * 1000)

    # First use
    res1 = g.allow_once("t3", "nonce3", now)
    assert res1 == "ALLOW"

    # Second use immediately: rejected
    res2 = g.allow_once("t3", "nonce3", now)
    assert res2 == "REJECT_EXIST"

    # Wait for expiration
    time.sleep(0.6)

    # After expiration: allowed again
    now2 = int(time.time() * 1000)
    res3 = g.allow_once("t3", "nonce3", now2)
    assert res3 == "ALLOW"
