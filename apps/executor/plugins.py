from typing import Any, Dict, Optional
import os
import time
import hmac
import hashlib
import json
import datetime
import random
import logging
import re

log = logging.getLogger("decisionos.exec.http")

# 간단한 python.call 핸들러 예시 (실전은 모듈 경로 임포트/검증 추가)
_USER_FUNCS = {}
# HTTP 플러그인 마스킹/계측
_MASK_HEADERS = {"authorization", "x-api-key", "x-secret", "proxy-authorization"}
_MASK_FIELDS = set([s.strip() for s in os.getenv("DECISIONOS_EXEC_HTTP_MASK_FIELDS", "password,secret,token").split(",") if s.strip()])
_EXEC_METRICS = {"attempts": 0, "retries": 0}

def register_python_func(name: str, fn):
    _USER_FUNCS[name] = fn

def python_call(decision: Dict[str, Any]) -> Any:
    spec = decision
    fn_name = spec.get("fn")
    args = spec.get("args", [])
    kwargs = spec.get("kwargs", {})
    if fn_name not in _USER_FUNCS:
        raise KeyError(f"unknown fn={fn_name}")
    return _USER_FUNCS[fn_name](*args, **kwargs)

def http_call_stub(decision: Dict[str, Any]) -> Any:
    # TODO: httpx 요청/서명/재시도. MVP는 스텁
    return {"status": "stub", "decision": decision}


# ---- real HTTP (httpx optional) ----
try:
    import httpx  # type: ignore
except Exception:
    httpx = None


def http_call(decision: Dict[str, Any]) -> Any:
    """
    decision = {
      "action": "http.call",
      "method": "POST",
      "url": "https://example/api",
      "headers": {"X-Foo":"bar"},
      "json": {"a":1},
      "timeout_sec": 3,
      "retries": 1
    }
    """
    if not httpx:
        raise RuntimeError("httpx not installed")

    method = (decision.get("method") or "GET").upper()
    url = decision["url"]
    headers = decision.get("headers") or {}
    json_body = decision.get("json")
    timeout = float(decision.get("timeout_sec") or os.getenv("DECISIONOS_EXEC_HTTP_TIMEOUT", "5"))
    retries = int(decision.get("retries") or os.getenv("DECISIONOS_EXEC_HTTP_RETRIES", "0"))
    backoff_base = float(os.getenv("DECISIONOS_EXEC_HTTP_BACKOFF_BASE", "0.1"))

    RETRY_ON_STATUS = {429, 500, 502, 503, 504}
    IMMEDIATE_FAIL_STATUS = {401, 403, 422}  # Auth/validation errors - no retry
    IDEMPOTENT = {"GET", "HEAD", "OPTIONS", "DELETE"}
    allow_non_idempotent = os.getenv("DECISIONOS_EXEC_HTTP_RETRY_NON_IDEMPOTENT", "0") == "1"

    def _should_retry(method: str, status_code: int, exc: Exception | None) -> bool:
        if exc is not None:
            return True
        if status_code in IMMEDIATE_FAIL_STATUS:
            return False  # Never retry auth/validation errors
        return status_code in RETRY_ON_STATUS

    def _sleep_backoff(base: float, attempt: int):
        delay = min(base * (2 ** attempt), 2.0)
        jitter = delay * (0.5 + random.random() * 0.5)
        time.sleep(jitter)

    if method not in IDEMPOTENT and not allow_non_idempotent:
        retries = 0

    def _maybe_hmac_headers(hdrs: dict, body_obj, method: str = "GET", url: str = "") -> dict:
        key = os.getenv("DECISIONOS_EXEC_HTTP_HMAC_KEY")
        key_id = os.getenv("DECISIONOS_EXEC_HTTP_KEY_ID", "default")
        if not key:
            return hdrs
        ts = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        canonical = json.dumps(body_obj or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        mac_src = "\n".join([method.upper(), url, ts, canonical]).encode("utf-8")
        sig = hmac.new(key.encode("utf-8"), mac_src, hashlib.sha256).hexdigest()
        out = dict(hdrs or {})
        out["X-DecisionOS-Timestamp"] = ts
        out["X-DecisionOS-Signature"] = sig
        out["X-Key-Id"] = key_id
        return out

    last_exc: Optional[Exception] = None
    headers = _maybe_hmac_headers(headers, json_body, method=method, url=url)
    for attempt in range(retries + 1):
        exc: Optional[Exception] = None
        try:
            with httpx.Client(timeout=timeout) as client:
                t0 = time.time()
                resp = client.request(method, url, headers=headers, json=json_body)
                if attempt < retries and _should_retry(method, resp.status_code, None):
                    _EXEC_METRICS["retries"] += 1
                    _sleep_backoff(backoff_base, attempt)
                    continue
                _EXEC_METRICS["attempts"] += 1
                if attempt > 0:
                    _EXEC_METRICS["retries"] += 1
                log.info(
                    "http_call result method=%s url=%s sc=%s lat_ms=%s headers=%s body=%s",
                    method,
                    url,
                    resp.status_code,
                    int((time.time() - t0) * 1000),
                    _mask_headers(headers),
                    _mask_json(json_body),
                )
                return {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "json": _safe_json(resp),
                    "text": None if "application/json" in resp.headers.get("content-type", "") else resp.text,
                }
        except Exception as ex:
            exc = ex
            last_exc = ex
        if attempt < retries and _should_retry(method, 0, exc):
            _sleep_backoff(backoff_base, attempt)
            continue
        if exc:
            raise exc
    if last_exc:
        raise last_exc
    raise RuntimeError("http_call failed without exception")


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def _mask_headers(h: dict) -> dict:
    out = {}
    for k, v in (h or {}).items():
        if k.lower() in _MASK_HEADERS:
            out[k] = "***"
        else:
            out[k] = v
    return out


def _mask_json(d):
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in d.items():
        if k.lower() in _MASK_FIELDS:
            out[k] = "***"
        else:
            out[k] = v
    return out
