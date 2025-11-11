from __future__ import annotations
import hashlib, json, os, pathlib
from typing import Any, Dict, Optional

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(path: str) -> Optional[str]:
    p = pathlib.Path(path)
    if not p.exists() or not p.is_file():
        return None
    return _sha256_bytes(p.read_bytes())

def make_etag(key: Dict[str, Any]) -> str:
    # 안정적 직렬화
    payload = json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f'W/"{_sha256_bytes(payload)}"'
