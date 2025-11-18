import os, time, pytest
from apps.ops.etag_store_redis import build_store, etag_v2_key, ETagValue

pytestmark = pytest.mark.gate_t

def test_inmemory_etag_basic(monkeypatch):
    monkeypatch.delenv("REDIS_DSN", raising=False)
    store = build_store()
    key = etag_v2_key("tenant", "/ops/cards", "demo")
    assert store.get(key) is None
    value = ETagValue(etag="W/demo", last_modified=time.time())
    store.set(key, value, ttl=2)
    got = store.get(key)
    assert got is not None and got.etag == "W/demo"
    invalidated = store.invalidate_prefix(key[:8])
    assert invalidated >= 1

@pytest.mark.skipif("REDIS_DSN" not in os.environ, reason="redis not configured")
def test_redis_etag(monkeypatch):
    store = build_store()
    key = etag_v2_key("tenant", "/ops/cards", "redis")
    store.set(key, ETagValue(etag="W/redis", last_modified=time.time()))
    assert store.get(key).etag == "W/redis"
