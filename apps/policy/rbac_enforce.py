# apps/policy/rbac_enforce.py
"""
RBAC enforcement middleware with hot-reload capability.

Security enhancements (v0.5.11u-5):
- Test mode default: OFF (DECISIONOS_RBAC_TEST_MODE=0)
- Production enforcement: test-mode ON causes boot failure
- X-Scopes header only allowed in dev/test environments
"""
from __future__ import annotations
import asyncio
import os
import fnmatch
import json
import time
import hashlib
import threading
import logging
from typing import List, Dict, Any, Optional, Set
from fastapi import Request, Response, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
import yaml

from apps.common.metrics import REG
from apps.metrics.registry import METRICS

log = logging.getLogger(__name__)


def _metrics_inc(name: str, labels: Dict[str, str] | None = None) -> None:
    """Increment metrics, ignoring errors during early boot or tests."""
    try:
        if METRICS:
            METRICS.inc(name, labels or {})
    except Exception:
        pass

# Environment detection
DECISIONOS_ENV = os.getenv("DECISIONOS_ENV", "dev").lower()

# RBAC test mode: default OFF (v0.5.11u-5 security hardening)
def _is_test_mode_enabled(raw: str | None = None) -> bool:
    """Return True when RBAC test mode is explicitly enabled and not in prod."""
    if DECISIONOS_ENV == "prod":
        return False
    raw_val = (raw if raw is not None else os.getenv("DECISIONOS_RBAC_TEST_MODE", "0")).strip().lower()
    return raw_val in ("1", "true", "yes")

_RBAC_TEST_MODE_RAW = os.getenv("DECISIONOS_RBAC_TEST_MODE", "0").strip().lower()
_RBAC_TEST_MODE = _is_test_mode_enabled(_RBAC_TEST_MODE_RAW)

# Production safety: test-mode must be OFF
if DECISIONOS_ENV == "prod" and _RBAC_TEST_MODE:
    raise RuntimeError(
        "FATAL: RBAC test-mode must be OFF in production. "
        "Set DECISIONOS_RBAC_TEST_MODE=0 or remove the variable."
    )

log.info(
    "rbac_init",
    extra={
        "env": DECISIONOS_ENV,
        "test_mode": _RBAC_TEST_MODE,
        "test_mode_raw": _RBAC_TEST_MODE_RAW,
    },
)

# Bypass paths (health checks, metrics)
_BYPASS = [
    p.strip()
    for p in os.getenv("DECISIONOS_RBAC_BYPASS_PREFIXES", "/healthz,/readyz,/metrics").split(",")
    if p.strip()
]

# Policy mode (AND/OR)
_MODE_ENV = os.getenv("DECISIONOS_RBAC_MODE")
_REQUIRE_ALL_ENV = (_MODE_ENV and _MODE_ENV.upper() == "AND") or (
    os.getenv("DECISIONOS_RBAC_OR", "1") == "0"
)


def _record_rbac_history(etag: str, event: str = "reload"):
    """Record RBAC reload in history tracker (avoid circular import)."""
    try:
        from apps.ops.cards.rbac_history import record_rbac_reload

        record_rbac_reload(etag, event)
    except ImportError:
        pass


def _sha256_of(path: str) -> str:
    """Compute SHA256 hash of file."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return ""


def _load_map(path: str) -> Dict[str, Any]:
    """Load RBAC map from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _extract_scopes_from_headers(req: Request) -> Set[str]:
    """
    Extract scopes from request headers.

    Security: X-Scopes header only allowed in test mode (dev/test environments).
    In production, this always returns empty set.
    """
    if _is_test_mode_enabled():
        # Test mode: allow X-Scopes header override
        hdr = req.headers.get("X-Scopes", "")
        if hdr:
            scopes = {s.strip() for s in hdr.split(",") if s.strip()}
            log.debug("rbac_test_mode_scopes", extra={"scopes": sorted(scopes)})
            return scopes

    return set()


def _extract_scopes_from_ctx(req: Request) -> Set[str]:
    """
    Extract scopes from request context (populated by auth middleware).

    Production path: Auth middleware validates JWT/session and sets req.state.scopes.
    """
    scopes = set(getattr(req.state, "scopes", []) or [])

    # Also check legacy header (X-DecisionOS-Scopes) for backwards compatibility
    legacy = req.headers.get("X-DecisionOS-Scopes", "")
    if legacy:
        scopes.update(s.strip() for s in legacy.split(",") if s.strip())

    return scopes


def _parse_scopes(req: Request) -> Set[str]:
    """
    Parse all scopes from request (context + headers).

    Priority:
    1. req.state.scopes (set by auth middleware)
    2. X-DecisionOS-Scopes header (legacy)
    3. X-Scopes header (test mode only)
    """
    scopes = _extract_scopes_from_ctx(req) | _extract_scopes_from_headers(req)

    # Wildcard support
    if "*" in scopes:
        return {"*"}

    return scopes


def _route_match(
    routes: List[Dict[str, Any]], path: str, method: str
) -> Optional[Dict[str, Any]]:
    """Find best matching route (longest path pattern match)."""
    method = method.upper()
    best = None
    for r in routes or []:
        pat = r.get("path", "")
        m = (r.get("method") or "*").upper()
        if fnmatch.fnmatch(path, pat) and (m == "*" or m == method):
            if not best or len(pat) > len(best.get("path", "")):
                best = r
    return best


def _allowed(req_scopes: Set[str], need: List[str], *, require_all: bool) -> bool:
    """Check if request scopes satisfy required scopes."""
    if "*" in req_scopes:
        return True
    if not need:
        return True
    if require_all:
        return all(s in req_scopes for s in need)
    return any(s in req_scopes for s in need)


class RbacMapState:
    """Hot-reloadable RBAC map state."""

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
        """Force reload RBAC map (must hold lock)."""
        self.routes = (_load_map(self.map_path) or {}).get("routes", [])
        self.sha = _sha256_of(self.map_path)
        self._next_check_ts = time.time() + self.reload_sec
        # Record initial load
        _metrics_inc("decisionos_rbac_map_reload_total", {"etag": self.sha or "EMPTY"})
        _record_rbac_history(self.sha, "initial")

    def ensure_fresh(self):
        """Check if RBAC map needs reload (hot-reload with SHA256 check)."""
        now = time.time()
        if now < self._next_check_ts:
            return
        REG.counter("rbac_reload_checks_total", "Total RBAC map reload checks").inc()
        with self._lock:
            if now < self._next_check_ts:
                return
            current = _sha256_of(self.map_path)
            if current and current != self.sha:
                REG.counter(
                    "rbac_reload_hit_total", "Total RBAC map reload hits (file changed)"
                ).inc()
                self.routes = (_load_map(self.map_path) or {}).get("routes", [])
                self.sha = current
                # New metrics: reload counter + ETag info
                _metrics_inc("decisionos_rbac_map_reload_total", {"etag": current or "EMPTY"})
                _record_rbac_history(current, "reload")
            self._next_check_ts = time.time() + self.reload_sec
        # Update ETag info metric
        REG.info("rbac_map_info", labels=("etag",), help_text="Current RBAC map ETag").set(
            (self.sha,)
        )


class RbacMapMiddleware(BaseHTTPMiddleware):
    """
    Hot-reloading RBAC middleware (default-deny).

    Security (v0.5.11u-5):
    - Test mode disabled by default in production
    - X-Scopes header only allowed in dev/test environments
    - Detailed denial logging for security audits
    """

    def __init__(
        self,
        app,
        map_path: str,
        default_deny: bool = True,
        reload_sec: Optional[int] = None,
        require_all: bool = False,
    ):
        super().__init__(app)
        self.default_deny = default_deny
        self.state = RbacMapState(
            map_path,
            reload_sec or int(os.getenv("DECISIONOS_RBAC_RELOAD_SEC", "2")),
            require_all=require_all,
        )

    async def dispatch(self, request: Request, call_next):
        # Bypass check (health, metrics)
        for prefix in _BYPASS:
            if request.url.path.startswith(prefix):
                _metrics_inc("decisionos_rbac_eval_total", {"result": "bypass"})
                return await call_next(request)

        self.state.ensure_fresh()
        matched = _route_match(self.state.routes, request.url.path, request.method)

        # Route match metrics
        if matched:
            REG.counter("rbac_route_matches_total", "Total RBAC route matches").inc()
            _metrics_inc("decisionos_rbac_route_match_total", {"match": "hit"})
        else:
            _metrics_inc("decisionos_rbac_route_match_total", {"match": "miss"})

        if not matched and self.default_deny:
            REG.counter("rbac_forbidden_total", "Total RBAC forbidden requests").inc()
            _metrics_inc("decisionos_rbac_denied_total", {"reason": "no_route_match"})
            log.warning(
                "rbac_deny_no_route",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "rbac_sha": self.state.sha,
                },
            )
            return Response(
                json.dumps(
                    {
                        "error": "forbidden",
                        "reason": "rbac.no_route_match",
                        "path": request.url.path,
                        "method": request.method,
                    }
                ),
                403,
                media_type="application/json",
            )

        if matched:
            need = matched.get("scopes", [])
            have = _parse_scopes(request)
            if not _allowed(have, need, require_all=self.state.require_all):
                REG.counter("rbac_forbidden_total", "Total RBAC forbidden requests").inc()
                _metrics_inc("decisionos_rbac_denied_total", {"reason": "missing_scope"})
                log.warning(
                    "rbac_deny_scope",
                    extra={
                        "path": request.url.path,
                        "need": need,
                        "have": sorted(have),
                        "test_mode": _RBAC_TEST_MODE,
                    },
                )
                return Response(
                    json.dumps(
                        {
                            "error": "forbidden",
                            "reason": "rbac.missing_scope",
                            "need": need,
                        }
                    ),
                    403,
                    media_type="application/json",
                )

        # Allowed
        REG.counter("rbac_allowed_total", "Total RBAC allowed requests").inc()
        _metrics_inc("decisionos_rbac_eval_total", {"result": "allow"})

        # Add RBAC map version to response header
        resp: Response = await call_next(request)
        resp.headers["X-RBAC-Map-ETag"] = self.state.sha or "missing"
        return resp


def require_scopes(*required: str, policy: str = "OR"):
    """
    FastAPI dependency for scope enforcement.

    Args:
        *required: Required scopes
        policy: "OR" (any scope matches) or "AND" (all scopes required)

    Security (v0.5.11u-5):
    - Test mode disabled by default in production
    - Detailed logging of denied requests
    """
    required_set = set(required)
    require_all = policy.upper() == "AND"

    async def _dep(request: Request):
        caller = _parse_scopes(request)
        if require_all:
            ok = required_set.issubset(caller)
        else:
            ok = bool(required_set & caller)

        if not ok:
            log.warning(
                "rbac_denied",
                extra={
                    "need": sorted(required_set),
                    "have": sorted(caller),
                    "policy": policy,
                    "test_mode": _is_test_mode_enabled(),
                },
            )
            _metrics_inc("decisionos_rbac_denied_total", {"reason": "scope_mismatch"})
            raise HTTPException(status_code=403, detail="forbidden")

        return True

    return Depends(_dep)
