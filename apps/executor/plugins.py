from typing import Any, Dict, Optional
import os
import time
import hmac
import hashlib
import json
import datetime

# 간단한 python.call 핸들러 예시 (실전은 모듈 경로 임포트/검증 추가)
_USER_FUNCS = {}

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

    def _maybe_hmac_headers(hdrs: dict, body_obj) -> dict:
        key = os.getenv("DECISIONOS_EXEC_HTTP_HMAC_KEY")
        key_id = os.getenv("DECISIONOS_EXEC_HTTP_KEY_ID", "default")
        if not key:
            return hdrs
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        canonical = json.dumps(body_obj or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sig = hmac.new(key.encode("utf-8"), (ts + "\n" + canonical).encode("utf-8"), hashlib.sha256).hexdigest()
        out = dict(hdrs or {})
        out["X-DecisionOS-Timestamp"] = ts
        out["X-DecisionOS-Signature"] = sig
        out["X-Key-Id"] = key_id
        return out

    headers = _maybe_hmac_headers(headers, json_body)

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, url, headers=headers, json=json_body)
                return {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "json": _safe_json(resp),
                    "text": None if "application/json" in resp.headers.get("content-type","") else resp.text,
                }
        except Exception as ex:
            last_exc = ex
            time.sleep(min(backoff_base * (2 ** attempt), 1.0))
    raise last_exc  # 마지막 실패를 표면화


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None
