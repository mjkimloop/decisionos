from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Query, Response

from apps.common.policy_loader import load_freeze_policy
from apps.judge.crypto import MultiKeyLoader, hmac_sign_canonical


@dataclass
class FreezeWindow:
    name: str
    services: Tuple[str, ...]
    allow_tags: Tuple[str, ...]
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    days: Optional[Tuple[int, ...]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tz: timezone = timezone.utc

    def _active_instant(self, now: datetime) -> bool:
        if self.start and self.end:
            return self.start <= now <= self.end
        if self.days and self.start_time and self.end_time:
            local = now.astimezone(self.tz)
            if local.weekday() not in self.days:
                return False
            start_dt = datetime.combine(local.date(), self.start_time.timetz(), tzinfo=self.tz)
            end_dt = datetime.combine(local.date(), self.end_time.timetz(), tzinfo=self.tz)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
                if local < start_dt:
                    start_dt -= timedelta(days=1)
            return start_dt <= local <= end_dt
        return False

    def matches_service(self, service: str) -> bool:
        return "*" in self.services or service in self.services

    def allow(self, labels: Sequence[str]) -> bool:
        if not self.allow_tags:
            return False
        norm = {label.strip().lower() for label in labels if label}
        return any(tag.lower() in norm for tag in self.allow_tags)

    def evaluate(self, now: datetime, service: str, labels: Sequence[str]) -> Tuple[bool, str]:
        if not self.matches_service(service):
            return False, ""
        if not self._active_instant(now):
            return False, ""
        if self.allow(labels):
            return False, f"window:{self.name}:allowed"
        return True, f"window:{self.name}"


def _weekday_index(name: str) -> int:
    table = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    return table[name.lower()]


def _parse_time(value: str) -> datetime:
    hh, mm = value.split(":")
    return datetime(1970, 1, 1, int(hh), int(mm), tzinfo=timezone.utc)


def _parse_windows(data: Dict[str, Any]) -> List[FreezeWindow]:
    windows: List[FreezeWindow] = []
    for item in data.get("windows", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("id") or "freeze"
        services = tuple(item.get("services") or ["*"])
        allow_tags = tuple(item.get("allow_tags") or [])
        tz_name = item.get("timezone", "UTC")
        tz = timezone.utc
        if tz_name.upper() != "UTC":
            try:
                from zoneinfo import ZoneInfo

                tz = ZoneInfo(tz_name)
            except Exception:
                tz = timezone.utc
        if item.get("start"):
            start = datetime.fromisoformat(item["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(item.get("end", item["start"]).replace("Z", "+00:00"))
            windows.append(
                FreezeWindow(
                    name=name,
                    services=services,
                    allow_tags=allow_tags,
                    start=start,
                    end=end,
                )
            )
            continue
        days_raw = item.get("days") or item.get("weekday")
        if days_raw:
            if isinstance(days_raw, str):
                days_raw = [days_raw]
            days = tuple(_weekday_index(day) for day in days_raw)
            start_time = _parse_time(item.get("start_time", "00:00"))
            end_time = _parse_time(item.get("end_time", "23:59"))
            windows.append(
                FreezeWindow(
                    name=name,
                    services=services,
                    allow_tags=allow_tags,
                    days=days,
                    start_time=start_time,
                    end_time=end_time,
                    tz=tz,
                )
            )
    return windows


def load_windows(path: Optional[str] = None) -> List[FreezeWindow]:
    policy = load_freeze_policy(path or "configs/change/freeze_windows.yaml")
    return _parse_windows(policy)


def _labels_from_env(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [token.strip() for token in value.replace(",", " ").split() if token.strip()]


def has_valid_break_glass(token: Optional[str] = None, manifest_path: str = "var/change/breakglass.json") -> bool:
    file = Path(manifest_path)
    if not file.exists():
        return False
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except Exception:
        return False
    manifest = data.get("manifest") or {}
    signature = data.get("signature") or {}
    if token and token != manifest.get("token"):
        return False
    expires_at = manifest.get("expires_at")
    if not expires_at or int(expires_at) < int(time.time()):
        return False
    loader = MultiKeyLoader(env_var="DECISIONOS_POLICY_KEYS", file_env="DECISIONOS_POLICY_KEYS_FILE")
    loader.force_reload()
    material = loader.get(signature.get("key_id", ""))
    if not material:
        return False
    computed = hmac_sign_canonical(manifest, material.secret)
    if computed != signature.get("hmac_sha256"):
        return False
    return True


def is_freeze_active(
    *,
    env: Optional[dict] = None,
    now: Optional[datetime] = None,
    service: str = "*",
    labels: Optional[Iterable[str]] = None,
    windows_path: Optional[str] = None,
) -> Tuple[bool, str]:
    env = env or os.environ
    labels_list = list(labels or []) or _labels_from_env(env.get("CHANGE_LABELS", ""))
    override_now = env.get("_FREEZE_NOW")
    if override_now and not now:
        now = datetime.fromisoformat(override_now.replace("Z", "+00:00"))
    now = now or datetime.now(tz=timezone.utc)
    service_name = service or env.get("DECISIONOS_SERVICE", "core")

    flag = env.get("DECISIONOS_FREEZE", "0")
    if flag in {"1", "true", "True"} and not any(lbl in {"urgent", "hotfix"} for lbl in labels_list):
        return True, "env:flag"
    flag_path = env.get("DECISIONOS_FREEZE_FILE", "var/release/freeze.flag")
    if flag_path and Path(flag_path).exists() and not has_valid_break_glass():
        return True, f"file:{flag_path}"

    windows = load_windows(windows_path)
    for window in windows:
        blocked, reason = window.evaluate(now, service_name, labels_list)
        if blocked:
            return True, reason
    return False, ""


# ===== ReadyZ compatibility (unchanged API) =====

CheckTuple = Tuple[bool, Dict[str, Any]]


def _key_grace_seconds() -> int:
    return int(os.getenv("DECISIONOS_JUDGE_KEY_GRACE_SEC", os.getenv("DECISIONOS_KEY_GRACE_SEC", "300")))


class ReadyzChecks:
    def __init__(
        self,
        *,
        multikey_fresh: Any,
        replay_ping: Any,
        clock_ok: Any,
        storage_ping: Any,
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


def _reason_codes(detail: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    for name, info in detail.items():
        if name == "ts":
            continue
        status = str(info.get("status", "unknown")) if isinstance(info, dict) else "unknown"
        if status.lower() in {"ok", "ready"}:
            continue
        code = info.get("reason") if isinstance(info, dict) else ""
        codes.append(f"{name}:{code or status}")
    return codes


def build_readyz_router(checks: ReadyzChecks, *, fail_closed: bool = True) -> APIRouter:
    router = APIRouter()

    @router.get("/readyz")
    def readyz(window: int = Query(default=0, ge=0), explain: int = Query(default=0)):
        ok, detail = checks.run()
        payload = {"status": "ready" if ok else "degraded", "checks": detail}
        payload["window"] = window or _key_grace_seconds()
        if explain:
            payload["reason_codes"] = _reason_codes(detail)
        status = 200 if ok or not fail_closed else 503
        return Response(content=json.dumps(payload), status_code=status, media_type="application/json")

    return router


def _key_check(loader: Any):
    def _inner():
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


def _replay_check(store: Any):
    def _inner():
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


def _clock_check():
    ref = os.getenv("DECISIONOS_CLOCK_REF_UNIX")
    max_skew = int(os.getenv("DECISIONOS_CLOCK_MAX_SKEW_SEC", os.getenv("DECISIONOS_CLOCK_SKEW_MAX", "0")))

    def _inner():
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


def _storage_check():
    base = Path(os.getenv("DECISIONOS_READY_STORAGE_DIR", "var/judge"))

    def _inner():
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


__all__ = [
    "FreezeWindow",
    "load_windows",
    "is_freeze_active",
    "has_valid_break_glass",
    "ReadyzChecks",
    "build_readyz_router",
    "default_readyz_checks",
    "check_ready",
]


def _parse_cli_labels(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.replace(",", " ").split() if part.strip()]


def cli(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Freeze guard CLI")
    parser.add_argument("--action", default="deploy")
    parser.add_argument("--service", default=os.getenv("DECISIONOS_SERVICE", "core"))
    parser.add_argument("--labels", default=os.getenv("CHANGE_LABELS", ""))
    parser.add_argument("--windows", default=None, help="Override freeze config path")
    parser.add_argument("--now", default=None, help="Override timestamp (ISO8601)")
    parser.add_argument("--echo", action="store_true")
    parser.add_argument("--allow-breakglass", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    labels = _parse_cli_labels(args.labels)
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    blocked, reason = is_freeze_active(service=args.service, labels=labels, now=now, windows_path=args.windows)
    if args.echo:
        print(f"[freeze] action={args.action} service={args.service} blocked={blocked} reason={reason}")
    if blocked and not (args.allow_breakglass and has_valid_break_glass()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
