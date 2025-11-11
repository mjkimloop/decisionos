import pytest
import time
from apps.judge.backpressure import (
    TokenBucket, CircuitBreaker, calculate_backoff_ms,
    RATE_LIMIT_PER_SECOND, BACKOFF_INITIAL_MS, BACKOFF_MAX_MS
)

@pytest.mark.gate_aj
def test_token_bucket_consume():
    """토큰 버킷 소비 테스트"""
    bucket = TokenBucket(capacity=10, refill_rate=10.0)

    # 10개 소비 성공
    for _ in range(10):
        assert bucket.consume() is True

    # 11번째는 실패 (토큰 부족)
    assert bucket.consume() is False

@pytest.mark.gate_aj
def test_token_bucket_refill():
    """토큰 버킷 리필 테스트"""
    bucket = TokenBucket(capacity=5, refill_rate=10.0)  # 초당 10개 리필

    # 전부 소비
    for _ in range(5):
        bucket.consume()

    assert bucket.consume() is False

    # 0.5초 대기 (5개 리필 예상)
    time.sleep(0.5)

    # 다시 소비 가능
    assert bucket.consume() is True

@pytest.mark.gate_aj
def test_circuit_breaker_open():
    """서킷 브레이커 오픈 동작 테스트"""
    breaker = CircuitBreaker(threshold=3, timeout_sec=1)

    def failing_func():
        raise Exception("test failure")

    # 3번 실패 → OPEN
    for _ in range(3):
        with pytest.raises(Exception):
            breaker.call(failing_func)

    stats = breaker.get_stats()
    assert stats["state"] == "open"
    assert stats["failure_count"] == 3

    # OPEN 상태에서는 함수 실행 안 됨
    with pytest.raises(Exception, match="Circuit breaker is OPEN"):
        breaker.call(failing_func)

@pytest.mark.gate_aj
def test_circuit_breaker_half_open():
    """서킷 브레이커 Half-Open 전환 테스트"""
    breaker = CircuitBreaker(threshold=2, timeout_sec=1, half_open_requests=2)

    def failing_func():
        raise Exception("test failure")

    # 2번 실패 → OPEN
    for _ in range(2):
        with pytest.raises(Exception):
            breaker.call(failing_func)

    assert breaker.get_stats()["state"] == "open"

    # 1초 대기 → Half-Open
    time.sleep(1.1)

    stats = breaker.get_stats()
    assert stats["state"] == "half_open"

@pytest.mark.gate_aj
def test_circuit_breaker_recovery():
    """서킷 브레이커 복구 테스트"""
    breaker = CircuitBreaker(threshold=2, timeout_sec=1, half_open_requests=2)

    def failing_func():
        raise Exception("test failure")

    def success_func():
        return "success"

    # 2번 실패 → OPEN
    for _ in range(2):
        with pytest.raises(Exception):
            breaker.call(failing_func)

    # 1초 대기 → Half-Open
    time.sleep(1.1)

    # 2번 성공 → Closed
    for _ in range(2):
        result = breaker.call(success_func)
        assert result == "success"

    stats = breaker.get_stats()
    assert stats["state"] == "closed"
    assert stats["failure_count"] == 0

@pytest.mark.gate_aj
def test_exponential_backoff():
    """지수 백오프 계산 테스트"""
    # attempt 0: 100ms
    assert calculate_backoff_ms(0) == BACKOFF_INITIAL_MS

    # attempt 1: 200ms
    assert calculate_backoff_ms(1) == BACKOFF_INITIAL_MS * 2

    # attempt 2: 400ms
    assert calculate_backoff_ms(2) == BACKOFF_INITIAL_MS * 4

    # attempt 10: 최대값 제한 (30초)
    assert calculate_backoff_ms(10) == BACKOFF_MAX_MS

@pytest.mark.gate_aj
def test_rate_limit_standard():
    """표준 레이트 리밋 상수 검증"""
    assert RATE_LIMIT_PER_SECOND == 100
    # 초당 100 요청 = 10ms per request
    assert 1000 / RATE_LIMIT_PER_SECOND == 10.0
