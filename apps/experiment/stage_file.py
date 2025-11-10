from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

Stage = Literal["stable", "canary", "promote", "abort"]

_STAGE_TXT_DEFAULT = Path("var/rollout/desired_stage.txt")
_MANIFEST_SUFFIX = ".manifest.json"
_KEY_JSON_ENV = "DECISIONOS_STAGE_KEYS"
_KEY_ENV = "DECISIONOS_STAGE_KEY"
_KEY_ID_ENV = "DECISIONOS_STAGE_KEY_ID"


@dataclass(frozen=True)
class StageState:
    stage: Stage
    sha256: str
    mtime: float


def _stage_path(path: Optional[str] = None) -> Path:
    return Path(path) if path else _STAGE_TXT_DEFAULT


def _manifest_path(stage_path: Path) -> Path:
    return stage_path.with_suffix(_MANIFEST_SUFFIX)


def _keys_configured() -> bool:
    return bool(os.getenv(_KEY_JSON_ENV)) or bool(os.getenv(_KEY_ENV))


def has_stage_key() -> bool:
    return _keys_configured()


def _load_keys() -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    raw = os.getenv(_KEY_JSON_ENV)
    if raw:
        try:
            data = json.loads(raw)
            for entry in data:
                kid = entry.get("key_id")
                secret = entry.get("secret")
                if kid and secret:
                    keys[str(kid)] = str(secret).encode("utf-8")
        except Exception:
            pass
    secret = os.getenv(_KEY_ENV)
    if secret:
        kid = os.getenv(_KEY_ID_ENV, "k1")
        keys.setdefault(kid, secret.encode("utf-8"))
    return keys


def _current_key() -> tuple[str, bytes]:
    keys = _load_keys()
    if not keys:
        raise RuntimeError("stage signing key not configured")
    preferred = os.getenv(_KEY_ID_ENV)
    if preferred and preferred in keys:
        return preferred, keys[preferred]
    return next(iter(keys.items()))


def _token_sha(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_sig(token: str, key: bytes) -> str:
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def write_stage_atomic(stage: Stage, path: Optional[str] = None) -> StageState:
    if not _keys_configured():
        raise RuntimeError("stage signing key not configured")
    stage_path = _stage_path(path)
    token = stage.strip()
    _atomic_write(stage_path, token + "\n")
    key_id, key = _current_key()
    manifest = {
        "token_sha256": _token_sha(token),
        "sig_hmac": _token_sig(token, key),
        "key_id": key_id,
        "algo": "HMAC-SHA256",
        "generated_at": _iso(time.time()),
    }
    _atomic_write(_manifest_path(stage_path), json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    stat = stage_path.stat()
    return StageState(stage=stage, sha256=_token_sha(token), mtime=stat.st_mtime)


def read_stage_with_hash(path: Optional[str] = None) -> StageState:
    stage_path = _stage_path(path)
    token, mtime = _read_or_repair(stage_path)
    return StageState(stage=token, sha256=_token_sha(token), mtime=mtime)


def read_stage_with_guard(path: Optional[str] = None) -> StageState:
    return read_stage_with_hash(path)


def guard_and_repair(path: Optional[str] = None) -> StageState:
    stage_path = _stage_path(path)
    if not _keys_configured():
        return StageState(stage="stable", sha256=_token_sha("stable"), mtime=time.time())
    return write_stage_atomic("stable", str(stage_path))


def manifest_path(path: Optional[str] = None) -> str:
    return str(_manifest_path(_stage_path(path)))


def _read_or_repair(stage_path: Path) -> tuple[Stage, float]:
    if not stage_path.exists():
        if _keys_configured():
            write_stage_atomic("stable", str(stage_path))
        return "stable", time.time()

    token = stage_path.read_text(encoding="utf-8").strip()
    manifest = _read_manifest(stage_path)

    if not _keys_configured():
        return "stable", time.time()

    if not manifest or not _verify_manifest(token, manifest):
        repaired = guard_and_repair(str(stage_path))
        return repaired.stage, repaired.mtime

    return token or "stable", stage_path.stat().st_mtime


def _read_manifest(stage_path: Path) -> Optional[dict]:
    manifest_file = _manifest_path(stage_path)
    if not manifest_file.exists():
        return None
    try:
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _verify_manifest(token: str, manifest: dict) -> bool:
    try:
        if manifest.get("token_sha256") != _token_sha(token):
            return False
        key_id = manifest.get("key_id")
        key = _load_keys().get(key_id)
        if not key:
            return False
        return manifest.get("sig_hmac") == _token_sig(token, key)
    except Exception:
        return False


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


__all__ = [
    "StageState",
    "Stage",
    "write_stage_atomic",
    "read_stage_with_hash",
    "read_stage_with_guard",
    "guard_and_repair",
    "manifest_path",
    "has_stage_key",
]
