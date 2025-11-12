import pytest
from apps.alerts.ratelimit import SlidingWindowRateLimiter
import time

@pytest.mark.gate_ops
def test_rate_limit_allows_then_blocks():
    rl = SlidingWindowRateLimiter(window_sec=1, max_events=2)
    assert rl.allow("k")
    assert rl.allow("k")
    assert rl.allow("k") is False
    time.sleep(1.05)
    assert rl.allow("k")
