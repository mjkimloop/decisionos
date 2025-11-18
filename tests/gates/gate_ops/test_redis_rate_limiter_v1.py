"""
Gate Ops — Redis Rate Limiter 테스트

Token Bucket 알고리즘 + Lua 스크립트 원자성 검증
"""
import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.gate_ops


@pytest.fixture
def mock_redis():
    """Mock Redis 클라이언트"""
    redis_mock = MagicMock()
    redis_mock.script_load.return_value = "mock_sha"
    redis_mock.evalsha.return_value = [1, 900, 0]
    return redis_mock


def test_rate_limiter_init():
    """레이트 리미터 초기화"""
    from apps.ops.ratelimit import RateLimiter

    redis_mock = MagicMock()
    redis_mock.script_load.return_value = "sha123"

    rl = RateLimiter(redis_mock)

    assert rl.redis == redis_mock
    assert rl._script_sha == "sha123"
    assert rl.policy is not None


def test_rate_limiter_check_global_allowed(mock_redis):
    """글로벌 레이트 리밋 - 허용"""
    from apps.ops.ratelimit import RateLimiter

    mock_redis.evalsha.return_value = [1, 900, 0]

    rl = RateLimiter(mock_redis)
    result = rl.check_global("/ops/cards")

    assert result.allowed is True
    assert result.remaining == 900
    assert result.retry_after == 0


def test_rate_limiter_check_global_denied(mock_redis):
    """글로벌 레이트 리밋 - 거부"""
    from apps.ops.ratelimit import RateLimiter

    mock_redis.evalsha.return_value = [0, 0, 60]

    rl = RateLimiter(mock_redis)
    result = rl.check_global("/ops/cards")

    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after == 60


def test_rate_limiter_check_tenant(mock_redis):
    """테넌트별 레이트 리밋"""
    from apps.ops.ratelimit import RateLimiter

    mock_redis.evalsha.return_value = [1, 800, 0]

    rl = RateLimiter(mock_redis)
    result = rl.check_tenant("t1", "/ops/cards")

    assert result.allowed is True
    assert result.remaining == 800


def test_rate_limiter_check_both(mock_redis):
    """글로벌 + 테넌트 양쪽 체크"""
    from apps.ops.ratelimit import RateLimiter

    mock_redis.evalsha.side_effect = [
        [1, 900, 0],
        [1, 800, 0],
    ]

    rl = RateLimiter(mock_redis)
    global_result, tenant_result = rl.check_both("t1", "/ops/cards")

    assert global_result.allowed is True
    assert tenant_result.allowed is True
