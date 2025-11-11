import pytest
from apps.ops.cache.metrics import ETagStoreMetrics

@pytest.mark.gate_ops
def test_metrics_hit_rate_calculation():
    """메트릭 히트율 계산 테스트"""
    m = ETagStoreMetrics()

    # 10번 히트, 2번 미스 = 83.33% 히트율
    for _ in range(10):
        m.record_hit()
    for _ in range(2):
        m.record_miss()

    stats = m.get_stats()
    assert stats["hits"] == 10
    assert stats["misses"] == 2
    assert stats["total_requests"] == 12
    assert 83.0 <= stats["hit_rate_pct"] <= 84.0

@pytest.mark.gate_ops
def test_metrics_zero_requests():
    """요청이 없을 때 메트릭 테스트"""
    m = ETagStoreMetrics()
    stats = m.get_stats()

    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["total_requests"] == 0
    assert stats["hit_rate_pct"] == 0.0

@pytest.mark.gate_ops
def test_metrics_reset():
    """메트릭 리셋 동작 테스트"""
    m = ETagStoreMetrics()

    m.record_hit()
    m.record_miss()
    m.record_put()
    m.record_error()

    assert m.get_stats()["hits"] == 1

    m.reset()
    stats = m.get_stats()

    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["puts"] == 0
    assert stats["errors"] == 0

@pytest.mark.gate_ops
def test_metrics_integration_with_inmemory():
    """InMemory 스토어와 메트릭 통합 테스트"""
    from apps.ops.cache.etag_store import InMemoryETagStore
    from apps.ops.cache.metrics import get_metrics

    # 메트릭 리셋
    get_metrics().reset()

    store = InMemoryETagStore()

    # Put 3번
    store.put("k1", {"v": 1})
    store.put("k2", {"v": 2})
    store.put("k3", {"v": 3})

    # Get 성공 2번 (히트)
    assert store.get("k1") is not None
    assert store.get("k2") is not None

    # Get 실패 1번 (미스)
    assert store.get("k999") is None

    stats = get_metrics().get_stats()
    assert stats["puts"] == 3
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate_pct"] >= 66.0  # 2/3 = 66.67%

@pytest.mark.gate_ops
def test_metrics_hit_rate_threshold():
    """목표 히트율 80% 달성 시나리오"""
    from apps.ops.cache.metrics import get_metrics

    get_metrics().reset()

    # 80번 히트, 20번 미스 = 정확히 80%
    for _ in range(80):
        get_metrics().record_hit()
    for _ in range(20):
        get_metrics().record_miss()

    stats = get_metrics().get_stats()
    assert stats["hit_rate_pct"] == 80.0
