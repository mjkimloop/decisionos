"""
ETag Store
Redis 기반 ETag 캐시 + InMemory fallback
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from typing import Any, Dict, Optional, Tuple


class InMemoryETagStore:
    """
    In-memory ETag snapshot store with TTL eviction

    Stores full snapshots (not just ETag strings) for Delta support
    """

    def __init__(self, default_ttl: int = 300):
        """Initialize in-memory store"""
        self.default_ttl = default_ttl
        self._snapshots: Dict[str, Tuple[Any, float]] = {}  # {etag: (snapshot, expire_ts)}

    def put(self, etag: str, snapshot: Any, ttl_sec: Optional[int] = None) -> None:
        """Store snapshot with TTL"""
        ttl = ttl_sec if ttl_sec is not None else self.default_ttl
        expire_ts = time.time() + ttl
        self._snapshots[etag] = (snapshot, expire_ts)

    def get(self, etag: str) -> Optional[Any]:
        """Get snapshot by ETag"""
        if etag in self._snapshots:
            snapshot, expire_ts = self._snapshots[etag]
            if time.time() < expire_ts:
                return snapshot
            else:
                # Expired, remove
                del self._snapshots[etag]
        return None

    def invalidate(self, pattern: str) -> int:
        """Invalidate snapshots matching pattern (simple prefix match)"""
        count = 0
        to_delete = []
        for key in self._snapshots:
            if key.startswith(pattern):
                to_delete.append(key)
        for key in to_delete:
            del self._snapshots[key]
            count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        # Evict expired first
        now = time.time()
        expired = [k for k, (_, exp) in self._snapshots.items() if exp <= now]
        for k in expired:
            del self._snapshots[k]

        return {
            "backend": "memory",
            "total_keys": len(self._snapshots),
        }


class RedisETagStore:
    """
    Redis-backed ETag snapshot store with TTL

    Stores full snapshots as JSON for Delta support
    """

    def __init__(self, redis_url: str, default_ttl: int = 300):
        """Initialize Redis store"""
        self.default_ttl = default_ttl
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._redis.ping()
        except Exception as e:
            raise RuntimeError(f"Redis connection failed: {e}")

    def put(self, etag: str, snapshot: Any, ttl_sec: Optional[int] = None) -> None:
        """Store snapshot with TTL"""
        ttl = ttl_sec if ttl_sec is not None else self.default_ttl
        key = f"etag:snapshot:{etag}"
        value = json.dumps(snapshot, separators=(",", ":"))
        self._redis.setex(key, ttl, value)

    def get(self, etag: str) -> Optional[Any]:
        """Get snapshot by ETag"""
        try:
            key = f"etag:snapshot:{etag}"
            value = self._redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"[ERROR] Redis get failed: {e}")
        return None

    def invalidate(self, pattern: str) -> int:
        """Invalidate snapshots matching pattern"""
        try:
            # Redis SCAN + DELETE pattern
            cursor = 0
            count = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=f"etag:snapshot:{pattern}*", count=100)
                if keys:
                    count += self._redis.delete(*keys)
                if cursor == 0:
                    break
            return count
        except Exception as e:
            print(f"[ERROR] Redis invalidate failed: {e}")
            return 0

    def stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        try:
            info = self._redis.info("stats")
            return {
                "backend": "redis",
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception:
            return {"backend": "redis", "error": True}


def build_etag_store() -> InMemoryETagStore | RedisETagStore:
    """
    Build ETag store based on environment configuration

    Environment variables:
    - DECISIONOS_ETAG_BACKEND: "memory" (default) or "redis"
    - DECISIONOS_REDIS_URL: Redis connection URL (for redis backend)
    - DECISIONOS_ETAG_TTL: Default TTL in seconds (default: 300)

    Returns:
        ETag store instance (Redis or InMemory fallback)
    """
    backend = os.environ.get("DECISIONOS_ETAG_BACKEND", "memory").lower()
    default_ttl = int(os.environ.get("DECISIONOS_ETAG_TTL", "300"))

    if backend == "redis":
        redis_url = os.environ.get("DECISIONOS_REDIS_URL")
        if not redis_url:
            print("[WARN] DECISIONOS_REDIS_URL not set, falling back to InMemory")
            return InMemoryETagStore(default_ttl)

        try:
            return RedisETagStore(redis_url, default_ttl)
        except Exception as e:
            print(f"[WARN] Redis backend failed: {e}, falling back to InMemory")
            return InMemoryETagStore(default_ttl)

    # Default: InMemory
    return InMemoryETagStore(default_ttl)


# Legacy compatibility
class ETagStore:
    """
    Legacy ETag storage (stores ETag strings only, not snapshots)

    Deprecated: Use build_etag_store() for snapshot support
    """

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._redis = None
        self._memory: Dict[str, Tuple[str, float]] = {}

        if redis_url:
            try:
                import redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except ImportError:
                print("[WARN] redis-py not installed, using InMemory fallback")
            except Exception as e:
                print(f"[WARN] Redis connection failed: {e}, using InMemory fallback")
                self._redis = None

    def _generate_etag(self, content: str) -> str:
        """Generate ETag from content"""
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        return f'"{hash_obj.hexdigest()[:16]}"'

    def get(self, key: str) -> Optional[str]:
        """Get ETag for key"""
        if self._redis:
            try:
                return self._redis.get(f"etag:{key}")
            except Exception as e:
                print(f"[ERROR] Redis get failed: {e}")
                return None
        else:
            if key in self._memory:
                etag, expire_ts = self._memory[key]
                if time.time() < expire_ts:
                    return etag
                else:
                    del self._memory[key]
            return None

    def set(self, key: str, content: str, ttl: Optional[int] = None) -> str:
        """Set ETag for key with content"""
        etag = self._generate_etag(content)
        ttl = ttl or self.default_ttl

        if self._redis:
            try:
                self._redis.setex(f"etag:{key}", ttl, etag)
            except Exception as e:
                print(f"[ERROR] Redis set failed: {e}")
        else:
            expire_ts = time.time() + ttl
            self._memory[key] = (etag, expire_ts)

        return etag

    def invalidate(self, key: str) -> bool:
        """Invalidate (delete) ETag for key"""
        if self._redis:
            try:
                return self._redis.delete(f"etag:{key}") > 0
            except Exception as e:
                print(f"[ERROR] Redis delete failed: {e}")
                return False
        else:
            if key in self._memory:
                del self._memory[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if ETag exists for key"""
        return self.get(key) is not None

    def stats(self) -> Dict[str, any]:
        """Get store statistics"""
        if self._redis:
            try:
                info = self._redis.info("stats")
                return {
                    "backend": "redis",
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
            except Exception:
                return {"backend": "redis", "error": True}
        else:
            return {
                "backend": "memory",
                "total_keys": len(self._memory),
            }


# Global instance (legacy)
_store: Optional[ETagStore] = None


def get_etag_store(redis_url: Optional[str] = None, default_ttl: int = 300) -> ETagStore:
    """
    Get or create global ETag store instance (legacy)

    Deprecated: Use build_etag_store() instead
    """
    global _store
    if _store is None:
        _store = ETagStore(redis_url, default_ttl)
    return _store
