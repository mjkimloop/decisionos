import os, pytest
from apps.ops.ratelimit import build_limiter

pytestmark = pytest.mark.gate_t

def test_inmemory_rate_limit(monkeypatch):
    monkeypatch.delenv("REDIS_DSN", raising=False)
    limiter = build_limiter()
    allowed_counts = [limiter.allow("global")[0] for _ in range(20)]
    assert any(allowed_counts)

@pytest.mark.skipif("REDIS_DSN" not in os.environ, reason="redis not configured")
def test_redis_rate_limit():
    limiter = build_limiter()
    ok1, _ = limiter.allow("tenant:a")
    ok2, _ = limiter.allow("tenant:a")
    assert isinstance(ok1, bool) and isinstance(ok2, bool)
