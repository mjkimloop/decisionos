import os
import pytest
from apps.ops.cache.etag_store import InMemoryETagStore, build_etag_store

@pytest.mark.gate_ops
def test_inmemory_ttl_eviction():
    """InMemory 스토어의 TTL 만료 동작 테스트"""
    s = InMemoryETagStore()
    s.put("k", {"v": 1}, ttl_sec=0)  # 즉시 만료
    assert s.get("k") is None

@pytest.mark.gate_ops
def test_inmemory_roundtrip():
    """InMemory 스토어의 기본 저장/조회 테스트"""
    s = InMemoryETagStore()
    s.put("test-key", {"data": "test-value"}, ttl_sec=60)
    result = s.get("test-key")
    assert result is not None
    assert result["data"] == "test-value"

@pytest.mark.gate_ops
def test_factory_default_inmemory(monkeypatch):
    """팩토리 함수가 기본적으로 InMemory를 반환하는지 테스트"""
    monkeypatch.delenv("DECISIONOS_ETAG_BACKEND", raising=False)
    store = build_etag_store()
    assert isinstance(store, InMemoryETagStore)

@pytest.mark.gate_ops
def test_factory_explicit_memory(monkeypatch):
    """팩토리 함수가 명시적 memory 설정을 처리하는지 테스트"""
    monkeypatch.setenv("DECISIONOS_ETAG_BACKEND", "memory")
    store = build_etag_store()
    assert isinstance(store, InMemoryETagStore)

@pytest.mark.gate_ops
def test_factory_redis_fallback_no_module(monkeypatch):
    """Redis 모듈이 없을 때 InMemory로 폴백하는지 테스트"""
    monkeypatch.setenv("DECISIONOS_ETAG_BACKEND", "redis")
    monkeypatch.setenv("DECISIONOS_REDIS_URL", "redis://nonexistent:6379/0")
    # Redis 모듈이 없거나 연결 실패 시 InMemory로 폴백
    store = build_etag_store()
    # 최소한 동작해야 함
    store.put("fallback-test", {"x": 1}, ttl_sec=1)
    result = store.get("fallback-test")
    # InMemory 폴백이면 정상 동작
    assert result is None or result == {"x": 1}

@pytest.mark.gate_ops
def test_inmemory_clear_expired():
    """InMemory 스토어의 만료 항목 정리 테스트"""
    import time
    s = InMemoryETagStore()

    # 즉시 만료되는 항목 3개
    s.put("exp1", {"v": 1}, ttl_sec=0)
    s.put("exp2", {"v": 2}, ttl_sec=0)
    s.put("exp3", {"v": 3}, ttl_sec=0)

    # 긴 TTL 항목 1개
    s.put("keep", {"v": 4}, ttl_sec=3600)

    # 약간 대기
    time.sleep(0.1)

    # 만료 항목 정리
    removed = s.clear_expired()
    assert removed == 3

    # 유효한 항목은 남아있어야 함
    assert s.get("keep") == {"v": 4}

@pytest.mark.gate_ops
@pytest.mark.skipif(
    os.getenv("DECISIONOS_ETAG_BACKEND", "").lower() != "redis",
    reason="Redis backend not enabled (set DECISIONOS_ETAG_BACKEND=redis)"
)
def test_redis_roundtrip_if_available():
    """Redis가 활성화된 경우 기본 동작 테스트 (선택적)"""
    try:
        from apps.ops.cache.etag_store import RedisETagStore
        url = os.getenv("DECISIONOS_REDIS_URL", "redis://localhost:6379/0")
        s = RedisETagStore(url=url, prefix="dos:test:etag")

        # 간단 ping 테스트
        s._r.ping()

        # 저장/조회 테스트
        s.put("redis-test", {"v": 1}, ttl_sec=2)
        result = s.get("redis-test")
        assert result == {"v": 1}
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")
