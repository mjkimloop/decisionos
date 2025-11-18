from __future__ import annotations

import os
import threading
import time
from typing import Optional, Tuple

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

RL_REFILL_PER_SEC = float(os.getenv("DECISIONOS_RL_REFILL_PER_SEC", "5"))
RL_BUCKET_CAP = int(os.getenv("DECISIONOS_RL_BUCKET_CAP", "10"))

LUA_TOKEN_BUCKET = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local cap = tonumber(ARGV[3])

local data = redis.call("HMGET", key, "tokens", "ts")
local tokens = tonumber(data[1]) or cap
local ts = tonumber(data[2]) or now
local delta = math.max(0, now - ts)
tokens = math.min(cap, tokens + delta * refill)
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end
redis.call("HMSET", key, "tokens", tokens, "ts", now)
redis.call("EXPIRE", key, 60)
return {allowed, tokens}
"""


class BaseRateLimiter:
    def allow(self, scope: str) -> Tuple[bool, float]:
        raise NotImplementedError


class InMemoryRateLimiter(BaseRateLimiter):
    def __init__(self, refill: float = RL_REFILL_PER_SEC, cap: int = RL_BUCKET_CAP) -> None:
        self.refill = refill
        self.cap = cap
        self._state: dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, scope: str) -> Tuple[bool, float]:
        now = time.time()
        with self._lock:
            tokens, ts = self._state.get(scope, (float(self.cap), now))
            tokens = min(self.cap, tokens + (now - ts) * self.refill)
            allowed = tokens >= 1.0
            if allowed:
                tokens -= 1.0
            self._state[scope] = (tokens, now)
            return allowed, tokens


class RedisRateLimiter(BaseRateLimiter):
    def __init__(self, dsn: Optional[str] = None, refill: float = RL_REFILL_PER_SEC, cap: int = RL_BUCKET_CAP) -> None:
        self.refill = refill
        self.cap = cap
        if not redis or not dsn:
            self._r = None
            self._script = None
            self._fallback = InMemoryRateLimiter(refill, cap)
        else:
            self._r = redis.Redis.from_url(dsn, decode_responses=True)  # type: ignore
            self._script = self._r.register_script(LUA_TOKEN_BUCKET)
            self._fallback = None

    def allow(self, scope: str) -> Tuple[bool, float]:
        if not self._r:
            return self._fallback.allow(scope)  # type: ignore
        allowed, tokens = self._script(keys=[f"rl:{scope}"], args=[time.time(), self.refill, self.cap])
        return bool(int(allowed)), float(tokens)


def build_limiter() -> BaseRateLimiter:
    dsn = os.getenv("REDIS_DSN")
    if dsn and redis:
        return RedisRateLimiter(dsn)
    return InMemoryRateLimiter()
