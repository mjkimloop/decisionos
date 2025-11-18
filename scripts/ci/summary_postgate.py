from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _read_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> None:
    idx = _read_json("var/evidence/index.json")
    gc = _read_json("var/evidence/gc-report.json")
    upload = _read_json("var/evidence/upload-report.json")
    dr = _read_json("var/dr/restore-report.json")
    print("## PostGate Summary")
    print(f"- Index items: {len(idx.get('items', []))}")
    print(f\"- GC dry-run counts: {gc.get('counts') or gc.get('totals')}\")
    print(f\"- Upload: mode={upload.get('mode')} counts={upload.get('counts')}\")
    print(f\"- DR: mode={dr.get('mode')} counts={dr.get('counts')}\")


if __name__ == "__main__":
    main()
