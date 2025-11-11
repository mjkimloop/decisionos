from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from apps.judge.keyloader_kms import load_from_ssm
from datetime import datetime, timezone

@dataclass
class KeyMaterial:
    key_id: str
    secret: bytes
    state: str  # "active" | "grace" | "retired"

class MultiKeyLoader:
    """ENV(JSON) 기반 멀티키 로더. 예:
    DECISIONOS_JUDGE_KEYS='[{"key_id":"k1","secret":"base64|hex|plain","state":"active"}]'
    """
    def __init__(self, env_var: str = "DECISIONOS_JUDGE_KEYS", file_env: str = "DECISIONOS_JUDGE_KEYS_FILE"):
        self.env_var = env_var
        self.file_env = file_env
        self._cache_ts = 0
        self._ttl = 5
        self._keys: Dict[str, KeyMaterial] = {}
        self._loaded_at: Optional[float] = None
        self._last_error: Optional[str] = None
        self._source_hash: Optional[str] = None
        self._file_mtime: Optional[float] = None

    def _parse_secret(self, s: str) -> bytes:
        if s.startswith("hex:"):
            return bytes.fromhex(s[4:])
        if s.startswith("b64:"):
            return base64.b64decode(s[4:])
        return s.encode("utf-8")

    def _read_source(self) -> str:
        data: List[Dict[str, Any]] = []
        file_path = os.getenv(self.file_env)
        if file_path:
            path = Path(file_path)
            if path.exists():
                try:
                    data.extend(json.loads(path.read_text(encoding="utf-8")) or [])
                except Exception:
                    pass
        raw_env = os.getenv(self.env_var)
        if raw_env:
            try:
                data.extend(json.loads(raw_env) or [])
            except Exception:
                pass
        if not data:
            legacy = os.getenv("DECISIONOS_JUDGE_HMAC_KEY")
            if legacy:
                data.append({"key_id": "legacy", "secret": legacy, "state": "active"})

        plugin = load_from_ssm()
        if plugin:
            data.extend(plugin)
        if not data:
            return "[]"
        return json.dumps(data)

    def force_reload(self) -> None:
        self._cache_ts = 0
        self._reload_if_needed(force=True)

    def _reload_if_needed(self, force: bool = False):
        file_path = os.getenv(self.file_env)
        if file_path:
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                mtime = None
        else:
            mtime = None
        if mtime is not None and self._file_mtime is not None and mtime != self._file_mtime:
            force = True
        self._file_mtime = mtime

        now = time.time()
        if not force and now - self._cache_ts < self._ttl:
            return
        source = self._read_source()
        try:
            data = json.loads(source)
        except Exception as exc:
            self._keys = {}
            self._cache_ts = now
            self._loaded_at = None
            self._last_error = f"{type(exc).__name__}: {exc}"
            self._source_hash = None
            return
        m: Dict[str, KeyMaterial] = {}
        for item in data:
            km = KeyMaterial(
                key_id=item["key_id"],
                secret=self._parse_secret(item["secret"]),
                state=item.get("state","active"),
            )
            m[km.key_id] = km
        self._keys = m
        self._cache_ts = now
        self._loaded_at = now
        self._last_error = None
        self._source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

    def get(self, key_id: str) -> Optional[KeyMaterial]:
        self._reload_if_needed()
        return self._keys.get(key_id)

    def choose_active(self) -> Optional[KeyMaterial]:
        self._reload_if_needed()
        for km in self._keys.values():
            if km.state == "active":
                return km
        return None

    def info(self) -> Dict[str, Optional[float] | Optional[str] | int]:
        self._reload_if_needed()
        age = None
        if self._loaded_at:
            age = max(0.0, time.time() - self._loaded_at)
        return {
            "key_count": len(self._keys),
            "loaded_at": datetime_from_timestamp(self._loaded_at),
            "loaded_at_epoch": self._loaded_at,
            "age_seconds": age,
            "last_error": self._last_error,
            "source_hash": self._source_hash,
        }


def datetime_from_timestamp(ts: Optional[float]) -> Optional[str]:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")

def canonical_json(obj) -> bytes:
    return json.dumps(obj, separators=(",",":"), sort_keys=True).encode("utf-8")

def hmac_sign(payload_obj, key: bytes) -> str:
    return hmac.new(key, canonical_json(payload_obj), hashlib.sha256).hexdigest()

def hmac_verify(payload_obj, key: bytes, signature_hex: str) -> bool:
    expected = hmac_sign(payload_obj, key)
    return hmac.compare_digest(expected, signature_hex)


def _coerce_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret
    try:
        return bytes.fromhex(secret)
    except ValueError:
        return secret.encode("utf-8")


def hmac_sign_canonical(payload_obj, secret: str | bytes) -> str:
    return hmac_sign(payload_obj, _coerce_secret(secret))


def hmac_verify_canonical(payload_obj, secret: str | bytes, signature_hex: str) -> bool:
    return hmac_verify(payload_obj, _coerce_secret(secret), signature_hex)

def verify_with_multikey(payload_obj, signature_hex: str, key_id: str, loader: MultiKeyLoader) -> Tuple[bool,str]:
    km = loader.get(key_id)
    if not km:
        return False, "key.missing"
    ok = hmac_verify(payload_obj, km.secret, signature_hex)
    if not ok:
        return False, "sig.mismatch"
    if km.state == "retired":
        return False, "key.retired"
    # grace는 검증만 허용
    return True, "ok"
