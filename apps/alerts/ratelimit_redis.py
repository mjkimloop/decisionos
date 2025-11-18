"""
Redis-based distributed rate limiter with LUA script for atomic sliding window.

For multi-process deployments where in-memory rate limiting is insufficient.
"""
import os
import time
from typing import Optional

# Redis client (lazy import)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# LUA script for atomic sliding window rate limiting
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local max_events = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- Remove events outside the window
local cutoff = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)

-- Count current events in window
local count = redis.call('ZCARD', key)

if count >= max_events then
    return 0  -- Rate limit exceeded
end

-- Add current event
redis.call('ZADD', key, now, now)

-- Set expiration to window + buffer
redis.call('EXPIRE', key, window + 60)

return 1  -- Allowed
"""

class RedisRateLimiter:
    """
    Redis-based distributed rate limiter using sorted sets.

    Uses LUA script for atomic operations to ensure consistency across multiple processes.
    """

    def __init__(self, redis_url: str, window_sec: int, max_events: int, key_prefix: str = "rl:"):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not available. Install with: pip install redis")

        self.redis_url = redis_url
        self.window_sec = window_sec
        self.max_events = max_events
        self.key_prefix = key_prefix

        # Parse Redis URL and create client
        self.client = redis.from_url(redis_url, decode_responses=True)

        # Register LUA script
        self.script_sha = self.client.script_load(SLIDING_WINDOW_LUA)

    def allow(self, key: str) -> bool:
        """
        Check if the request is allowed under rate limit.

        Returns True if allowed, False if rate limited.
        """
        full_key = f"{self.key_prefix}{key}"
        now = time.time()

        try:
            # Execute LUA script
            result = self.client.evalsha(
                self.script_sha,
                1,  # Number of keys
                full_key,
                self.window_sec,
                self.max_events,
                now
            )
            return bool(result)
        except redis.exceptions.NoScriptError:
            # Script not loaded, reload and retry
            self.script_sha = self.client.script_load(SLIDING_WINDOW_LUA)
            result = self.client.evalsha(
                self.script_sha,
                1,
                full_key,
                self.window_sec,
                self.max_events,
                now
            )
            return bool(result)
        except Exception as e:
            print(f"[ERROR] Redis rate limiter failed: {e}")
            # Fail open: allow request on error (can be changed to fail-closed)
            return True

    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key"""
        full_key = f"{self.key_prefix}{key}"
        self.client.delete(full_key)

    def get_count(self, key: str) -> int:
        """Get current event count in window"""
        full_key = f"{self.key_prefix}{key}"
        now = time.time()
        cutoff = now - self.window_sec

        # Remove old events
        self.client.zremrangebyscore(full_key, '-inf', cutoff)

        # Return count
        return self.client.zcard(full_key)

    def close(self) -> None:
        """Close Redis connection"""
        self.client.close()

def build_rate_limiter(window_sec: int = 300, max_events: int = 20, key_prefix: str = "rl:"):
    """
    Build rate limiter based on environment configuration.

    If DECISIONOS_REDIS_URL is set, use Redis. Otherwise, fall back to in-memory.
    """
    redis_url = os.environ.get("DECISIONOS_REDIS_URL")

    if redis_url and REDIS_AVAILABLE:
        try:
            return RedisRateLimiter(redis_url, window_sec, max_events, key_prefix)
        except Exception as e:
            print(f"[WARN] Failed to create Redis rate limiter: {e}, falling back to in-memory")

    # Fallback to in-memory rate limiter
    from apps.alerts.ratelimit import SlidingWindowRateLimiter
    return SlidingWindowRateLimiter(window_sec, max_events)
