import os
import threading
from typing import Optional

import httpx

_lock = threading.Lock()
_client: Optional[httpx.Client] = None


def get_http_client() -> httpx.Client:
    global _client
    if _client:
        return _client
    with _lock:
        if _client:
            return _client
        timeout = float(os.getenv("DECISIONOS_EXEC_HTTP_TIMEOUT", "5"))
        max_keepalive = int(os.getenv("DECISIONOS_EXEC_HTTP_POOL_MAX_KEEPALIVE", "100"))
        max_conn = int(os.getenv("DECISIONOS_EXEC_HTTP_POOL_MAX_CONNECTIONS", "200"))
        keepalive_expiry = float(os.getenv("DECISIONOS_EXEC_HTTP_POOL_KEEPALIVE_EXPIRY", "20"))
        http2 = os.getenv("DECISIONOS_EXEC_HTTP_ENABLE_HTTP2", "1") in ("1", "true", "yes")

        limits = httpx.Limits(
            max_keepalive_connections=max_keepalive,
            max_connections=max_conn,
            keepalive_expiry=keepalive_expiry,
        )
        _client = httpx.Client(
            timeout=timeout,
            limits=limits,
            http2=http2 and _http2_available(),
            headers={"User-Agent": "decisionos-exec/1"},
        )
        return _client


def _http2_available() -> bool:
    try:
        import h2  # noqa
        return True
    except Exception:
        return False
