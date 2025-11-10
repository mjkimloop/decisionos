from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .snapshot import sha256_text

CORE_KEYS = ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]
OPTIONAL_KEYS = ["perf", "perf_judge", "judges", "canary"]


def recompute_integrity(evidence: Dict[str, Any]) -> Dict[str, Any]:
    core = {key: evidence[key] for key in CORE_KEYS if key in evidence}
    for key in OPTIONAL_KEYS:
        if key in evidence and evidence[key] is not None:
            core[key] = evidence[key]
    core_json = json.dumps(core, ensure_ascii=False, sort_keys=True)
    evidence.setdefault("integrity", {})["signature_sha256"] = sha256_text(core_json)
    return evidence


def merge_blocks(evidence_path: str | Path, **blocks: Any) -> Dict[str, Any]:
    path = Path(evidence_path)
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in blocks.items():
        if value is None:
            continue
        data[key] = value
    recompute_integrity(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return data


__all__ = ["merge_blocks", "recompute_integrity"]
