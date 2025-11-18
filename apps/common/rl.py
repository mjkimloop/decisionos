from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

try:  # optional redis dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None

DEFAULT_WINDOW_SEC = int(os.getenv("DECISIONOS_RL_WINDOW_SEC", "60"))
DEFAULT_MAX_REQUESTS = int(os.getenv("DECISIONOS_RL_MAX_REQUESTS", "600"))
DEFAULT_BURST = int(os.getenv("DECISIONOS_RL_BURST", "120"))


@dataclass
class AllowDecision:
    allowed: bool
    remaining: float


class BaseRateLimiter:
    def allow(self, scope: str) -> AllowDecision:
        raise NotImplementedError


class InMemoryRateLimiter(BaseRateLimiter):
    def __init__(self, refill_per_sec: float, burst: int) -> None:
        self.refill = refill_per_sec
        self.cap = float(max(1, burst))
        self._state: dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, scope: str) -> AllowDecision:
        now = time.time()
        with self._lock:
            tokens, ts = self._state.get(scope, (self.cap, now))
            tokens = min(self.cap, tokens + (now - ts) * self.refill)
            allowed = tokens >= 1.0
            if allowed:
                tokens -= 1.0
            self._state[scope] = (tokens, now)
            return AllowDecision(allowed=allowed, remaining=max(0.0, tokens))


class RedisRateLimiter(BaseRateLimiter):
    LUA = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local refill = tonumber(ARGV[2])
    local cap = tonumber(ARGV[3])

    local tokens = tonumber(redis.call("HGET", key, "tokens")) or cap
    local ts = tonumber(redis.call("HGET", key, "ts")) or now
    local delta = math.max(0, now - ts)
    tokens = math.min(cap, tokens + delta * refill)
    local allowed = 0
    if tokens >= 1 then
      tokens = tokens - 1
      allowed = 1
    end
    redis.call("HMSET", key, "tokens", tokens, "ts", now)
    redis.call("EXPIRE", key, 120)
    return {allowed, tokens}
    """

    def __init__(self, dsn: str, refill_per_sec: float, burst: int) -> None:
        self._client = redis.Redis.from_url(dsn, decode_responses=False)  # type: ignore[attr-defined]
        self._script = self._client.register_script(self.LUA)
        self.refill = refill_per_sec
        self.cap = float(max(1, burst))

    def allow(self, scope: str) -> AllowDecision:
        result = self._script(keys=[f"rl:{scope}"], args=[time.time(), self.refill, self.cap])
        allowed_flag, tokens = result
        return AllowDecision(bool(int(allowed_flag)), float(tokens))


def _compute_refill(window: int, max_requests: int) -> float:
    window = max(1, window)
    return max(0.1, max_requests / window)


def build_rate_limiter() -> Optional[BaseRateLimiter]:
    if os.getenv("DECISIONOS_RL_ENABLE", "0") != "1":
        return None
    window = int(os.getenv("DECISIONOS_RL_WINDOW_SEC", str(DEFAULT_WINDOW_SEC)))
    max_requests = int(os.getenv("DECISIONOS_RL_MAX_REQUESTS", str(DEFAULT_MAX_REQUESTS)))
    burst = int(os.getenv("DECISIONOS_RL_BURST", str(DEFAULT_BURST)))
    refill = _compute_refill(window, max_requests)
    backend = os.getenv("DECISIONOS_RL_BACKEND", "memory").lower()
    if backend == "redis":
        redis_dsn = os.getenv("DECISIONOS_REDIS_DSN") or os.getenv("REDIS_DSN")
        if redis and redis_dsn:
            try:
                return RedisRateLimiter(redis_dsn, refill, burst)
            except Exception:
                pass
    return InMemoryRateLimiter(refill, burst)


def should_enable() -> bool:
    return os.getenv("DECISIONOS_RL_ENABLE", "0") == "1"


def _fingerprint(ip: str, route: str, scope: str) -> str:
    raw = f"{ip}|{route}|{scope}".encode()
    return hashlib.sha256(raw).hexdigest()


def attach_rate_limit(app, *, window_sec: Optional[int] = None, max_requests: Optional[int] = None, burst: Optional[int] = None):
    limiter = build_rate_limiter()
    if not limiter:
        return app
    window = window_sec or int(os.getenv("DECISIONOS_RL_WINDOW_SEC", str(DEFAULT_WINDOW_SEC)))
    max_req = max_requests or int(os.getenv("DECISIONOS_RL_MAX_REQUESTS", str(DEFAULT_MAX_REQUESTS)))
    burst_cap = burst or int(os.getenv("DECISIONOS_RL_BURST", str(DEFAULT_BURST)))

    def _scopes_from_request(request) -> str:
        header = request.headers.get("x-decisionos-scopes") or request.headers.get("x-decisionos-scope")
        if header:
            return header
        env = os.getenv("DECISIONOS_ALLOW_SCOPES", "")
        return env or "*"

    def _client_ip(request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "0.0.0.0"

    @app.middleware("http")
    async def _rl(request, call_next):
        scope = _scopes_from_request(request)
        key = _fingerprint(_client_ip(request), request.url.path, scope)
        decision = limiter.allow(key)
        if not decision.allowed:
            from fastapi import Response

            retry = str(window)
            headers = {"Retry-After": retry, "X-RateLimit-Limit": str(max_req + burst_cap)}
            return Response("Too Many Requests", status_code=429, headers=headers, media_type="text/plain")
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Remaining", str(int(decision.remaining)))
        response.headers.setdefault("X-RateLimit-Limit", str(max_req + burst_cap))
        return response

    return app


__all__ = [
    "AllowDecision",
    "BaseRateLimiter",
    "InMemoryRateLimiter",
    "RedisRateLimiter",
    "build_rate_limiter",
    "attach_rate_limit",
    "should_enable",
]
