from __future__ import annotations

import hashlib
import os
import time
from typing import Optional, Tuple

from apps.metrics.registry import METRICS
import json
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

_PATH_DEFAULT = os.getenv("DECISIONOS_RBAC_MAP_PATH", "configs/policy/rbac_map.yaml")
_CHECK_INTERVAL = int(os.getenv("DECISIONOS_RBAC_MAP_CHECK_SEC", "15"))

_state = {"etag": "", "loaded_at": 0.0, "map": {}}


def _calc_etag(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _load() -> Tuple[str, dict]:
    path = os.getenv("DECISIONOS_RBAC_MAP_PATH", _PATH_DEFAULT)
    inline = os.getenv("DECISIONOS_RBAC_MAP", "")
    try:
        if inline.strip():
            s = inline
        else:
            with open(path, "r", encoding="utf-8") as f:
                s = f.read()
        etag = _calc_etag(s)
        m = {}
        try:
            if "yaml" in globals() and "safe_load" in dir(yaml):  # type: ignore[name-defined]
                m = yaml.safe_load(s) or {}  # type: ignore[name-defined]
            else:
                m = json.loads(s)
        except Exception:
            m = {}
        return etag, m
    except FileNotFoundError:
        return "", {}
    except Exception:
        return _state["etag"], _state["map"]


def maybe_reload(now: Optional[float] = None) -> None:
    """관측 전용 핫리로드: 맵 집행은 rbac_enforce가 담당."""
    now = now or time.time()
    if _state["loaded_at"] and (now - _state["loaded_at"] < _CHECK_INTERVAL):
        return
    _state["loaded_at"] = now
    etag, m = _load()
    if not etag:
        etag = str(int(now * 1000))
    if etag != _state.get("etag", ""):
        _state.update({"etag": etag, "map": m})
        METRICS.inc_sync("decisionos_rbac_map_reload_total", {"result": "hit"})
        METRICS.set_sync("decisionos_rbac_map_etag_seen", int(etag[:8], 16) % 10_000_000)
    else:
        METRICS.inc_sync("decisionos_rbac_map_reload_total", {"result": "miss"})


def current_etag() -> str:
    return _state["etag"]


def current_map() -> dict:
    return _state["map"]


# Simple hot reloader class (synchronous) for route-level scope lookup.
class RbacHotReloader:
    def __init__(self, path: Optional[str] = None):
        self._path = path or os.getenv("DECISIONOS_RBAC_MAP_PATH")
        self._etag: Optional[str] = None
        self._mtime: float = 0.0
        self._map: dict = {}
        self.hits = 0
        self.misses = 0

    def _calc_etag(self, raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    def maybe_reload(self):
        if not self._path or not os.path.exists(self._path):
            return
        m = os.path.getmtime(self._path)
        if m <= self._mtime:
            return
        with open(self._path, "rb") as f:
            raw = f.read()
        try:
            self._map = json.loads(raw.decode("utf-8"))
        except Exception:
            self._map = {}
        self._etag = self._calc_etag(raw)
        self._mtime = m

    def required_scopes_for(self, route: str, method: str) -> Optional[list[str]]:
        self.maybe_reload()
        rules = self._map.get(route) or {}
        scopes = rules.get(method.upper()) or rules.get("*")
        if scopes:
            self.hits += 1
        else:
            self.misses += 1
        return scopes

    @property
    def etag(self) -> Optional[str]:
        return self._etag


_hot = RbacHotReloader()


def get_required_scopes(route: str, method: str) -> Optional[list[str]]:
    return _hot.required_scopes_for(route, method)


def rbac_map_etag() -> Optional[str]:
    return _hot.etag
