from fastapi import APIRouter, Response
from typing import Dict, Any
import os

router = APIRouter()

@router.get("/ops/health/etag-store")
def get_etag_store_health() -> Dict[str, Any]:
    """ETag 저장소 헬스 체크 및 메트릭"""
    from .cache.metrics import get_metrics
    from .cache.etag_store import _ETAG_STORE

    metrics = get_metrics().get_stats()

    # 백엔드 타입 감지
    backend_type = "unknown"
    backend_config = {}

    if hasattr(_ETAG_STORE, '_r'):
        # Redis 백엔드
        backend_type = "redis"
        try:
            _ETAG_STORE._r.ping()
            redis_healthy = True
            # Redis INFO 명령으로 추가 메트릭 수집
            info = _ETAG_STORE._r.info("stats")
            backend_config = {
                "url": os.environ.get("DECISIONOS_REDIS_URL", "redis://localhost:6379/0"),
                "prefix": os.environ.get("DECISIONOS_ETAG_REDIS_PREFIX", "dos:cards:etag"),
                "healthy": True,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            redis_healthy = False
            backend_config = {
                "healthy": False,
                "error": str(e)
            }
    elif hasattr(_ETAG_STORE, '_data'):
        # InMemory 백엔드
        backend_type = "memory"
        try:
            data_size = len(_ETAG_STORE._data)
            backend_config = {
                "healthy": True,
                "entries": data_size,
            }
        except Exception as e:
            backend_config = {
                "healthy": False,
                "error": str(e)
            }

    return {
        "backend": backend_type,
        "backend_config": backend_config,
        "metrics": metrics,
        "thresholds": {
            "target_hit_rate_pct": 80.0,
            "max_error_rate_pct": 1.0,
        }
    }

@router.get("/ops/health/redis")
def get_redis_health(response: Response) -> Dict[str, Any]:
    """Redis 연결 헬스 체크"""
    backend = os.environ.get("DECISIONOS_ETAG_BACKEND", "memory").lower()

    if backend != "redis":
        response.status_code = 503
        return {
            "healthy": False,
            "reason": "Redis backend not configured",
            "backend": backend
        }

    from .cache.etag_store import _ETAG_STORE

    if not hasattr(_ETAG_STORE, '_r'):
        response.status_code = 503
        return {
            "healthy": False,
            "reason": "Redis backend not initialized (fallback to memory)"
        }

    try:
        _ETAG_STORE._r.ping()
        info = _ETAG_STORE._r.info("server")

        return {
            "healthy": True,
            "redis_version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        response.status_code = 503
        return {
            "healthy": False,
            "error": str(e)
        }
