from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_KEYS = ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly", "integrity"]
CORE_KEYS = ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]
OPTIONAL_BLOCKS = ["perf", "perf_judge", "judges", "canary"]


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _core_signature(data: Dict[str, Any]) -> str:
    core = {key: data.get(key) for key in CORE_KEYS}
    for block in OPTIONAL_BLOCKS:
        if block in data and data[block] is not None:
            core[block] = data[block]
    payload = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tier_for(path: Path) -> str:
    return "LOCKED" if path.name.endswith(".locked.json") else "WIP"


def scan_dir(root: str = "var/evidence", redact_config: Optional[str] = None) -> Dict[str, Any]:
    """
    Scan evidence directory and build index

    Args:
        root: Evidence directory path
        redact_config: Optional path to PII redaction rules config

    Returns:
        Index dictionary with files and summary
    """
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    files: List[Dict[str, Any]] = []
    latest_mtime = 0.0
    redacted_count = 0

    for entry in sorted(root_path.glob("*.json")):
        if entry.name == "index.json":
            continue
        try:
            stat = entry.stat()
            file_sha = _sha256_file(entry)
            data = json.loads(entry.read_text(encoding="utf-8"))

            # Apply PII redaction if config provided
            if redact_config:
                try:
                    from .redact import redact_evidence
                    data = redact_evidence(data, redact_config)
                    redacted_count += 1
                except Exception as e:
                    print(f"[WARN] Redaction failed for {entry.name}: {e}")
                    # On redaction failure, exclude from index (fail-closed)
                    files.append({
                        "path": entry.name,
                        "sha256": file_sha,
                        "size": stat.st_size,
                        "mtime": _iso(stat.st_mtime),
                        "tier": _tier_for(entry),
                        "locked_at": None,
                        "tampered": True,
                        "error": f"redaction_failed: {e}",
                        "tenant": None,
                        "generated_at": None,
                    })
                    continue

            missing = [key for key in REQUIRED_KEYS if key not in data]
            tampered = bool(missing)
            if not tampered:
                sig = (data.get("integrity") or {}).get("signature_sha256")
                # Recalculate signature after redaction
                expected = _core_signature(data)
                tampered = sig is None or sig != expected

            tier = _tier_for(entry)
            meta = data.get("meta") or {}
            files.append(
                {
                    "path": entry.name,
                    "sha256": file_sha,  # Original file SHA (before redaction)
                    "size": stat.st_size,
                    "mtime": _iso(stat.st_mtime),
                    "tier": tier,
                    "locked_at": _iso(stat.st_mtime) if tier == "LOCKED" else None,
                    "tampered": tampered,
                    "redacted": redact_config is not None,
                    "tenant": meta.get("tenant"),
                    "generated_at": meta.get("generated_at"),
                }
            )
        except Exception as exc:
            files.append(
                {
                    "path": entry.name,
                    "sha256": "",
                    "size": entry.stat().st_size if entry.exists() else 0,
                    "mtime": _iso(entry.stat().st_mtime) if entry.exists() else _iso(0),
                    "tier": _tier_for(entry),
                    "locked_at": None,
                    "tampered": True,
                    "error": str(exc),
                    "tenant": None,
                    "generated_at": None,
                }
            )
        finally:
            try:
                stat = entry.stat()
                latest_mtime = max(latest_mtime, stat.st_mtime)
            except FileNotFoundError:
                continue
    summary = {
        "count": len(files),
        "tampered": sum(1 for f in files if f.get("tampered")),
        "wip": sum(1 for f in files if f.get("tier") == "WIP"),
        "locked": sum(1 for f in files if f.get("tier") == "LOCKED"),
        "redacted": redacted_count if redact_config else 0,
    }
    last_updated = _iso(latest_mtime) if latest_mtime else None
    return {
        "generated_at": _iso(datetime.now(timezone.utc).timestamp()),
        "last_updated": last_updated,
        "root": str(root_path),
        "files": files,
        "summary": summary,
        "redaction": {
            "enabled": redact_config is not None,
            "config": redact_config,
            "count": redacted_count,
        } if redact_config else None,
    }


def write_index(root: str = "var/evidence", out: str | None = None, redact_config: Optional[str] = None) -> str:
    """
    Write evidence index to file

    Args:
        root: Evidence directory path
        out: Output path (default: {root}/index.json)
        redact_config: Optional path to PII redaction rules config

    Returns:
        Path to written index file
    """
    index = scan_dir(root, redact_config=redact_config)
    out_path = Path(out) if out else Path(root) / "index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return str(out_path)


def scan_evidence_dir(root: str = "var/evidence", redact_config: Optional[str] = None) -> Dict[str, Any]:
    """
    Scan evidence directory (wrapper for scan_dir)

    Args:
        root: Evidence directory path
        redact_config: Optional path to PII redaction rules config

    Returns:
        Index dictionary
    """
    return scan_dir(root, redact_config=redact_config)


__all__ = ["scan_dir", "scan_evidence_dir", "write_index"]
