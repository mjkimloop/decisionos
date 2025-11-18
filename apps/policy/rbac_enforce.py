# apps/policy/rbac_enforce.py
from __future__ import annotations
import asyncio
import os, fnmatch, json, time, hashlib, threading
from typing import List, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
import yaml

from apps.common.metrics import REG
from apps.metrics.registry import METRICS

def _record_rbac_history(etag: str, event: str = "reload"):
    """Record RBAC reload in history tracker (避免循环导入)."""
    try:
        from apps.ops.cards.rbac_history import record_rbac_reload
        record_rbac_reload(etag, event)
    except ImportError:
        pass

_BYPASS = [p.strip() for p in os.getenv("DECISIONOS_RBAC_BYPASS_PREFIXES", "/healthz,/readyz,/metrics").split(",") if p.strip()]
_TEST_MODE = os.getenv("DECISIONOS_RBAC_TEST_MODE", "1") == "1"
_MODE_ENV = os.getenv("DECISIONOS_RBAC_MODE")
_REQUIRE_ALL_ENV = (_MODE_ENV and _MODE_ENV.upper() == "AND") or (os.getenv("DECISIONOS_RBAC_OR", "1") == "0")

def _sha256_of(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return ""

def _load_map(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _parse_scopes(req: Request) -> List[str]:
    raw = req.headers.get("x-decisionos-scopes") or os.getenv("DECISIONOS_ALLOW_SCOPES", "")
    if _TEST_MODE:
        raw = req.headers.get("x-scopes") or raw
    if raw.strip() == "*":
        return ["*"]
    parts = [p.strip() for p in raw.replace(",", " ").split()]
    return [p for p in parts if p]

def _route_match(routes: List[Dict[str, Any]], path: str, method: str) -> Optional[Dict[str, Any]]:
    method = method.upper()
    best = None
    for r in routes or []:
        pat = r.get("path", "")
        m = (r.get("method") or "*").upper()
        if fnmatch.fnmatch(path, pat) and (m == "*" or m == method):
            if not best or len(pat) > len(best.get("path", "")):
                best = r
    return best

def _allowed(req_scopes: List[str], need: List[str], *, require_all: bool) -> bool:
    if "*" in req_scopes:
        return True
    if not need:
        return True
    if require_all:
        return all(s in req_scopes for s in need)
    return any(s in req_scopes for s in need)

class RbacMapState:
    def __init__(self, map_path: str, reload_sec: int, require_all: bool):
        self.map_path = map_path
        self.reload_sec = max(1, reload_sec)
        self.require_all = require_all
        self.routes: List[Dict[str, Any]] = []
        self.sha = ""
        self._next_check_ts = 0.0
        self._lock = threading.Lock()
        self._force_reload_unlocked()

    def _force_reload_unlocked(self):
        self.routes = (_load_map(self.map_path) or {}).get("routes", [])
        self.sha = _sha256_of(self.map_path)
        self._next_check_ts = time.time() + self.reload_sec
        # Record initial load
        asyncio.create_task(METRICS.inc("decisionos_rbac_map_reload_total", {"etag": self.sha or "EMPTY"}))
        _record_rbac_history(self.sha, "initial")

    def ensure_fresh(self):
        now = time.time()
        if now < self._next_check_ts:
            return
        REG.counter("rbac_reload_checks_total", "Total RBAC map reload checks").inc()
        with self._lock:
            if now < self._next_check_ts:
                return
            current = _sha256_of(self.map_path)
            if current and current != self.sha:
                REG.counter("rbac_reload_hit_total", "Total RBAC map reload hits (file changed)").inc()
                self.routes = (_load_map(self.map_path) or {}).get("routes", [])
                self.sha = current
                # New metrics: reload counter + ETag info
                asyncio.create_task(METRICS.inc("decisionos_rbac_map_reload_total", {"etag": current or "EMPTY"}))
                _record_rbac_history(current, "reload")
            self._next_check_ts = time.time() + self.reload_sec
        # Update ETag info metric (both old and new)
        REG.info("rbac_map_info", labels=("etag",), help_text="Current RBAC map ETag").set((self.sha,))

class RbacMapMiddleware(BaseHTTPMiddleware):
    """
    Hot-reloading RBAC middleware (default-deny).
    AND/OR 정책은 require_all으로 제어(기본 OR).
    """
    def __init__(self, app, map_path: str, default_deny: bool = True,
                 reload_sec: Optional[int] = None, require_all: bool = False):
        super().__init__(app)
        self.default_deny = default_deny
        self.state = RbacMapState(
            map_path,
            reload_sec or int(os.getenv("DECISIONOS_RBAC_RELOAD_SEC", "2")),
            require_all=require_all,
        )

    async def dispatch(self, request: Request, call_next):
        # Bypass check
        for prefix in _BYPASS:
            if request.url.path.startswith(prefix):
                await METRICS.inc("decisionos_rbac_eval_total", {"result": "bypass"})
                return await call_next(request)

        self.state.ensure_fresh()
        matched = _route_match(self.state.routes, request.url.path, request.method)

        # Route match metrics
        if matched:
            REG.counter("rbac_route_matches_total", "Total RBAC route matches").inc()
            await METRICS.inc("decisionos_rbac_route_match_total", {"match": "hit"})
        else:
            await METRICS.inc("decisionos_rbac_route_match_total", {"match": "miss"})

        if not matched and self.default_deny:
            REG.counter("rbac_forbidden_total", "Total RBAC forbidden requests").inc()
            await METRICS.inc("decisionos_rbac_eval_total", {"result": "deny"})
            return Response(json.dumps({
                "error": "forbidden", "reason": "rbac.no_route_match",
                "path": request.url.path, "method": request.method, "rbac_sha": self.state.sha
            }), 403, media_type="application/json")

        if matched:
            need = matched.get("scopes", [])
            have = _parse_scopes(request)
            if not _allowed(have, need, require_all=self.state.require_all):
                REG.counter("rbac_forbidden_total", "Total RBAC forbidden requests").inc()
                await METRICS.inc("decisionos_rbac_eval_total", {"result": "deny"})
                return Response(json.dumps({
                    "error": "forbidden", "reason": "rbac.missing_scope",
                    "need": need, "have": have, "rbac_sha": self.state.sha
                }), 403, media_type="application/json")

        # Allowed
        REG.counter("rbac_allowed_total", "Total RBAC allowed requests").inc()
        await METRICS.inc("decisionos_rbac_eval_total", {"result": "allow"})

        # 맵 버전 ETag 힌트를 응답 헤더로
        resp: Response = await call_next(request)
        resp.headers["X-RBAC-Map-ETag"] = self.state.sha or "missing"
        return resp

def require_scopes(*required: str, require_all: bool = False):
    async def _dep(request: Request):
        have = _parse_scopes(request)
        ok = _allowed(have, list(required), require_all=require_all)
        if not ok:
            raise HTTPException(status_code=403, detail={
                "reason":"rbac.missing_scope","need":list(required),"have":have
            })
        return True
    return Depends(_dep)
