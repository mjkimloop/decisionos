from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_KEYS = ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly", "integrity"]
CORE_KEYS = ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _core_signature(obj: Dict[str, Any]) -> str:
    core = {key: obj[key] for key in CORE_KEYS if key in obj}
    core_json = json.dumps(core, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(core_json.encode("utf-8")).hexdigest()


def scan_evidence_dir(root: str | Path) -> Dict[str, Any]:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for file_path in sorted(root_path.glob("*.json")):
        try:
            stat = file_path.stat()
            file_sha = _sha256_file(file_path)
            data = _load_json(file_path)
            missing = [key for key in REQUIRED_KEYS if key not in data]
            sig = (data.get("integrity") or {}).get("signature_sha256")
            tampered = bool(missing)
            if not tampered:
                tampered = sig is None or sig != _core_signature(data)
            rows.append(
                {
                    "path": str(file_path),
                    "size": stat.st_size,
                    "mtime": int(stat.st_mtime),
                    "sha256": file_sha,
                    "version": (data.get("meta") or {}).get("version"),
                    "tenant": (data.get("meta") or {}).get("tenant"),
                    "generated_at": (data.get("meta") or {}).get("generated_at"),
                    "tampered": tampered,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "path": str(file_path),
                    "size": file_path.stat().st_size if file_path.exists() else 0,
                    "mtime": int(file_path.stat().st_mtime) if file_path.exists() else 0,
                    "sha256": "",
                    "error": str(exc),
                    "tampered": True,
                }
            )
    return {
        "root": str(root_path),
        "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(rows),
        "items": rows,
    }


__all__ = ["scan_evidence_dir"]
