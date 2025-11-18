"""
Gate Tenant — Redis namespace isolation tests (ETag + Replay Guard)
"""
import pytest
import time

try:
    import redis
    REDIS_AVAILABLE = True
    # Try connecting
    r = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=1)
    r.ping()
except Exception:
    REDIS_AVAILABLE = False

pytestmark = pytest.mark.gate_tenant


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
def test_etag_store_tenant_isolation():
    """Test that ETag store isolates keys by tenant"""
    import redis
    from apps.storage.etag_store import ETagStore

    r = redis.Redis(host="localhost", port=6379, db=0)

    # Create stores for two different tenants
    store_tenant_a = ETagStore(r, ttl_ms=60000, tenant_id="tenant-a")
    store_tenant_b = ETagStore(r, ttl_ms=60000, tenant_id="tenant-b")

    # Both tenants use same resource key
    resource_key = "test-resource"
    payload_a = {"value": "tenant-a-data"}
    payload_b = {"value": "tenant-b-data"}

    # Put payloads for both tenants
    store_tenant_a.put(resource_key, payload_a)
    store_tenant_b.put(resource_key, payload_b)

    # Retrieve payloads
    result_a = store_tenant_a.get(resource_key)
    result_b = store_tenant_b.get(resource_key)

    # Each tenant should get their own data
    import json
    assert json.loads(result_a["val"]) == payload_a
    assert json.loads(result_b["val"]) == payload_b

    # ETags should be different
    assert result_a["etag"] != result_b["etag"]


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
def test_etag_store_tenant_cas_isolation():
    """Test that CAS operations are isolated by tenant"""
    import redis
    from apps.storage.etag_store import ETagStore

    r = redis.Redis(host="localhost", port=6379, db=0)

    store_tenant_a = ETagStore(r, ttl_ms=60000, tenant_id="tenant-a")
    store_tenant_b = ETagStore(r, ttl_ms=60000, tenant_id="tenant-b")

    resource_key = "test-cas"
    payload_initial = {"version": 1}
    payload_update_a = {"version": 2, "tenant": "a"}
    payload_update_b = {"version": 2, "tenant": "b"}

    # Both tenants put initial version
    store_tenant_a.put(resource_key, payload_initial)
    store_tenant_b.put(resource_key, payload_initial)

    # Get ETags
    result_a = store_tenant_a.get(resource_key)
    result_b = store_tenant_b.get(resource_key)
    etag_a = result_a["etag"]
    etag_b = result_b["etag"]

    # Tenant A updates with correct ETag
    cas_result_a = store_tenant_a.cas(resource_key, payload_update_a, etag_a)
    assert cas_result_a == "OK"

    # Tenant B should still be able to update (different namespace)
    cas_result_b = store_tenant_b.cas(resource_key, payload_update_b, etag_b)
    assert cas_result_b == "OK"

    # Verify both updates succeeded independently
    import json
    final_a = store_tenant_a.get(resource_key)
    final_b = store_tenant_b.get(resource_key)

    assert json.loads(final_a["val"])["tenant"] == "a"
    assert json.loads(final_b["val"])["tenant"] == "b"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
def test_replay_guard_tenant_isolation():
    """Test that Replay Guard isolates nonces by tenant"""
    import redis
    from apps.storage.replay_store_redis import ReplayGuard

    r = redis.Redis(host="localhost", port=6379, db=0)

    guard_tenant_a = ReplayGuard(r, window_ms=60000, tenant_id="tenant-a")
    guard_tenant_b = ReplayGuard(r, window_ms=60000, tenant_id="tenant-b")

    # Same nonce for both tenants
    nonce = "nonce-123"
    now_ms = int(time.time() * 1000)

    # Both tenants should be able to use the same nonce (isolated)
    result_a = guard_tenant_a.allow_once(nonce, now_ms)
    result_b = guard_tenant_b.allow_once(nonce, now_ms)

    assert result_a == "ALLOW"
    assert result_b == "ALLOW"

    # Second attempt should be rejected for each tenant
    result_a2 = guard_tenant_a.allow_once(nonce, now_ms + 100)
    result_b2 = guard_tenant_b.allow_once(nonce, now_ms + 100)

    assert result_a2 == "REJECT_EXIST"
    assert result_b2 == "REJECT_EXIST"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
def test_replay_guard_tenant_override():
    """Test that tenant parameter overrides default tenant"""
    import redis
    from apps.storage.replay_store_redis import ReplayGuard

    r = redis.Redis(host="localhost", port=6379, db=0)

    # Create guard with default tenant
    guard = ReplayGuard(r, window_ms=60000, tenant_id="default")

    nonce = "nonce-456"
    now_ms = int(time.time() * 1000)

    # Use nonce with tenant override
    result_a = guard.allow_once(nonce, now_ms, tenant="tenant-override-a")
    result_b = guard.allow_once(nonce, now_ms, tenant="tenant-override-b")

    # Both should succeed (different tenants)
    assert result_a == "ALLOW"
    assert result_b == "ALLOW"

    # Using default tenant should also succeed (different namespace)
    result_default = guard.allow_once(nonce, now_ms)
    assert result_default == "ALLOW"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
def test_tenant_mixed_input_fail_closed():
    """Test that mixing tenant data fails closed (cross-contamination protection)"""
    import redis
    from apps.storage.etag_store import ETagStore

    r = redis.Redis(host="localhost", port=6379, db=0)

    store_a = ETagStore(r, ttl_ms=60000, tenant_id="tenant-a")
    store_b = ETagStore(r, ttl_ms=60000, tenant_id="tenant-b")

    resource_key = "shared-key"

    # Tenant A writes data
    payload_a = {"tenant": "a", "secret": "data-a"}
    store_a.put(resource_key, payload_a)

    # Tenant B tries to read with wrong ETag from tenant A
    result_a = store_a.get(resource_key)
    etag_a = result_a["etag"]

    # Tenant B's CAS with tenant A's ETag should fail (different namespace)
    payload_b = {"tenant": "b", "secret": "data-b"}
    cas_result = store_b.cas(resource_key, payload_b, etag_a)

    # Should be MISSING because tenant B namespace doesn't have this key yet
    assert cas_result == "MISSING"

    # Tenant B's data should remain isolated
    result_b = store_b.get(resource_key)
    assert not result_b  # Empty dict (key doesn't exist in tenant B namespace)
