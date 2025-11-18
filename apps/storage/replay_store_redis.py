"""
Replay Guard with Redis Lua script for atomic nonce checking.

Prevents replay attacks by ensuring each nonce is used only once within a time window.
"""
import time
from pathlib import Path
from typing import Literal

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

ReplayResult = Literal["ALLOW", "REJECT_EXIST", "REJECT_CLOCKSKEW", "INVALID"]


class ReplayGuard:
    """
    Redis-backed replay attack prevention.

    Uses SET NX with TTL to ensure nonce uniqueness.
    Validates timestamp to prevent clock skew attacks.

    Tenant Isolation:
    - All keys are namespaced by tenant_id: dos:replay:{tenant}:{nonce}
    """

    def __init__(self, r, window_ms: int = 300000, tenant_id: str = "default"):
        """
        Initialize replay guard.

        Args:
            r: Redis client
            window_ms: Time window for nonce validity (milliseconds)
            tenant_id: Default tenant identifier for namespace isolation
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package required for ReplayGuard")

        self.r = r
        self.window = window_ms
        self.tenant_id = tenant_id

        # Load Lua script
        lua_path = Path(__file__).parent / "redis" / "lua" / "replay_guard.lua"
        with open(lua_path, "r", encoding="utf-8") as f:
            self.sha = self.r.script_load(f.read())

    def allow_once(
        self,
        nonce: str,
        now_ms: int,
        skew_ms: int = 60000,
        tenant: str = None
    ) -> ReplayResult:
        """
        Check if nonce is allowed (first use within time window).

        Args:
            nonce: Unique nonce string
            now_ms: Current timestamp in milliseconds
            skew_ms: Allowed clock skew (default 60 seconds)
            tenant: Tenant identifier (overrides default if provided)

        Returns:
            - "ALLOW": First use, allowed
            - "REJECT_EXIST": Nonce already used (replay attack)
            - "REJECT_CLOCKSKEW": Timestamp outside allowed range
        """
        # Use provided tenant or fall back to default
        tenant_id = tenant if tenant is not None else self.tenant_id
        key = f"dos:replay:{tenant_id}:{nonce}"

        result = self.r.evalsha(
            self.sha,
            1,
            key,
            str(now_ms),
            str(now_ms - skew_ms),
            str(now_ms + skew_ms),
            str(self.window)
        )

        return result.decode() if isinstance(result, bytes) else result
