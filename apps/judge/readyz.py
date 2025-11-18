from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import APIRouter, Query, Response
from apps.judge.metrics_readyz import READYZ_METRICS
from apps.metrics.registry import METRICS

def _record_readyz_window(ok: bool, reasons: Optional[List[str]]):
    """Record readyz check in window tracker (避免循环导入)."""
    try:
        from apps.ops.cards.readyz_window import record_readyz_check
        record_readyz_check(ok, reasons)
    except ImportError:
        pass

CheckFn = Callable[[], Tuple[bool, Dict[str, Any]]]
_WINDOW_SEC = float(os.getenv("DECISIONOS_READY_WINDOW_SEC", "60"))
_WINDOW_MAX = int(os.getenv("DECISIONOS_READY_MAX_SAMPLES", "120"))
_WINDOW = deque(maxlen=_WINDOW_MAX)


def _key_grace_seconds() -> int:
    return int(os.getenv("DECISIONOS_JUDGE_KEY_GRACE_SEC", os.getenv("DECISIONOS_KEY_GRACE_SEC", "300")))


def _maybe_override(env_key: str) -> Optional[Tuple[bool, Dict[str, Any]]]:
    val = os.getenv(env_key)
    if val is None or val == "":
        return None
    if str(val).lower() == "fail":
        return False, {"status": "error", "reason": f"{env_key.lower()}"}
    return True, {"status": "ok", "reason": f"{env_key.lower()}"}


class ReadyzChecks:
    def __init__(
        self,
        *,
        multikey_fresh: CheckFn,
        replay_ping: CheckFn,
        clock_ok: CheckFn,
        storage_ping: CheckFn,
    ):
        self._checks = {
            "keys": multikey_fresh,
            "replay_store": replay_ping,
            "clock": clock_ok,
            "storage": storage_ping,
        }

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        details: Dict[str, Dict[str, Any]] = {}
        overall = True
        for name, func in self._checks.items():
            try:
                ok, info = func()
            except Exception as exc:
                ok = False
                info = {"status": "error", "reason": str(exc)}
            details[name] = info
            overall = overall and ok
        details["ts"] = int(time.time())
        return overall, details


def _reason_codes(detail: Dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for name, info in detail.items():
        if name == "ts":
            continue
        status = str(info.get("status", "unknown")) if isinstance(info, dict) else "unknown"
        if status.lower() in {"ok", "ready"}:
            continue
        code = info.get("reason") if isinstance(info, dict) else ""
        if code:
            reasons.append(f"{name}:{code}")
        else:
            reasons.append(f"{name}:{status}")
    return reasons


def build_readyz_router(checks: ReadyzChecks, *, fail_closed: bool = True) -> APIRouter:
    router = APIRouter()

    @router.get("/readyz")
    async def readyz(window: int = Query(default=0, ge=0), explain: int = Query(default=0)):
        ok, detail = checks.run()
        READYZ_METRICS.observe(ok)
        ratios = READYZ_METRICS.ratios()

        # New metrics: readyz status counter
        status_label = "ready" if ok else "degraded"
        await METRICS.inc("decisionos_readyz_total", {"result": status_label})

        # Record failure reason codes
        reason_codes = []
        if not ok:
            reason_codes = _reason_codes(detail)
            for reason in reason_codes:
                # Split "check:code" format
                parts = reason.split(":", 1)
                check = parts[0] if len(parts) > 0 else "unknown"
                code = parts[1] if len(parts) > 1 else "unknown"
                await METRICS.inc("decisionos_readyz_reason_total", {"check": check, "code": code})

        # Record in window tracker
        _record_readyz_window(ok, reason_codes if not ok else None)

        now = time.time()
        reasons = _reason_codes(detail)
        _WINDOW.append({"t": now, "ok": ok, "reasons": reasons})
        cutoff = now - (window or _WINDOW_SEC)
        while _WINDOW and _WINDOW[0]["t"] < cutoff:
            _WINDOW.popleft()

        samples = list(_WINDOW)
        fail_count = sum(1 for item in samples if not item["ok"])
        payload = {
            "status": status_label,
            "checks": detail,
            "window": {
                "window_sec": window or _WINDOW_SEC,
                "samples": len(samples),
                "fail": fail_count,
                "ok": len(samples) - fail_count,
                "last": samples[-1] if samples else None,
            },
            "metrics": ratios,
        }
        # ETA: remaining seconds before key grace expires (if available)
        keys_info = detail.get("keys", {})
        age = keys_info.get("age_seconds")
        if isinstance(age, (int, float)):
            remaining = max(0, _key_grace_seconds() - age)
            payload["eta_seconds"] = {"keys": remaining}
        if explain:
            payload["reason_codes"] = _reason_codes(detail)
        status = 200 if ok or not fail_closed else 503
        return Response(content=json.dumps(payload), status_code=status, media_type="application/json")

    return router


def _key_check(loader: Any) -> CheckFn:
    def _inner():
        ov = _maybe_override("DECISIONOS_READY_KEYS")
        if ov:
            return ov
        if not loader:
            return False, {"status": "error", "reason": "loader.missing"}
        try:
            info = loader.info()
        except AttributeError:
            try:
                count = len(loader.keys())
            except Exception as exc:
                return False, {"status": "error", "reason": f"keys.load_failed:{exc}"}
            status = "ok" if count > 0 else "missing"
            return count > 0, {"status": status, "key_count": count}
        states = info.get("states") or {}
        key_count = info.get("key_count") or 0
        age = info.get("age_seconds")
        if key_count <= 0 or states.get("active", 0) <= 0:
            return False, {"status": "missing", "key_count": key_count, "states": states}
        grace = _key_grace_seconds()
        if age and age > grace:
            return False, {"status": "stale", "key_count": key_count, "states": states, "age_seconds": age}
        return True, {"status": "ok", "key_count": key_count, "states": states, "age_seconds": age}

    return _inner


def _replay_check(store: Any) -> CheckFn:
    def _inner():
        ov = _maybe_override("DECISIONOS_READY_REPLAY")
        if ov:
            return ov
        if not store:
            return False, {"status": "error", "reason": "replay_store.missing"}
        try:
            if hasattr(store, "ping"):
                store.ping()
                return True, {"status": "ok", "backend": store.__class__.__name__}
            if hasattr(store, "health_check"):
                healthy, info = store.health_check()
                if not healthy:
                    return False, {"status": "unhealthy", "reason": info}
        except Exception as exc:
            return False, {"status": "error", "reason": str(exc)}
        return True, {"status": "ok", "backend": store.__class__.__name__}

    return _inner


def _clock_check() -> CheckFn:
    ref = os.getenv("DECISIONOS_CLOCK_REF_UNIX")
    max_skew = int(os.getenv("DECISIONOS_CLOCK_MAX_SKEW_SEC", os.getenv("DECISIONOS_CLOCK_SKEW_MAX", "0")))

    def _inner():
        ov = _maybe_override("DECISIONOS_READY_CLOCK")
        if ov:
            return ov
        if not ref or max_skew <= 0:
            return True, {"status": "ok", "reason": "not_configured"}
        try:
            expected = int(ref)
            diff = abs(int(time.time()) - expected)
            ok = diff <= max_skew
            return ok, {"status": "ok" if ok else "skew", "diff": diff, "max_skew": max_skew}
        except Exception as exc:
            return False, {"status": "error", "reason": str(exc)}

    return _inner


def _storage_check() -> CheckFn:
    base = Path(os.getenv("DECISIONOS_READY_STORAGE_DIR", "var/judge"))

    def _inner():
        ov = _maybe_override("DECISIONOS_READY_STORE")
        if ov:
            return ov
        try:
            base.mkdir(parents=True, exist_ok=True)
            probe = base / "readyz.probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True, {"status": "ok", "path": str(base)}
        except OSError as exc:
            return False, {"status": "error", "reason": str(exc), "path": str(base)}

    return _inner


def default_readyz_checks(key_loader: Any = None, replay_store: Optional[Any] = None) -> ReadyzChecks:
    return ReadyzChecks(
        multikey_fresh=_key_check(key_loader),
        replay_ping=_replay_check(replay_store),
        clock_ok=_clock_check(),
        storage_ping=_storage_check(),
    )


def check_ready(key_loader: Any = None, replay_store: Optional[Any] = None) -> Tuple[bool, Dict[str, Any]]:
    checks = default_readyz_checks(key_loader, replay_store)
    return checks.run()


__all__ = ["ReadyzChecks", "build_readyz_router", "default_readyz_checks", "check_ready"]
