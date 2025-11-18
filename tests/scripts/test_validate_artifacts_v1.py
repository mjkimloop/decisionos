from __future__ import annotations

import json
from pathlib import Path

from scripts.ci.validate_artifacts import validate_artifacts


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_validate_all_success(tmp_path):
    index = tmp_path / "index.json"
    _write(index, {"generated_at": "now", "items": [{"path": "a.json", "sha256": "abc"}]})
    gc = tmp_path / "gc.json"
    _write(gc, {"totals": {"scanned": 3}})
    upload = tmp_path / "upload.json"
    _write(upload, {"mode": "stub", "counts": {"uploaded": 1, "skipped": 0, "failed": 0}})
    dr = tmp_path / "dr.json"
    _write(dr, {"counts": {"restored": 1, "failed": 0}})

    ok, details = validate_artifacts(
        {"index": str(index), "gc": str(gc), "upload": str(upload), "dr": str(dr)}
    )
    assert ok
    assert details["index"]["status"] == "ok"
    assert details["gc"]["status"] == "ok"
    assert details["upload"]["status"] == "ok"
    assert details["dr"]["status"] == "ok"


def test_validate_missing_file(tmp_path):
    ok, details = validate_artifacts({"index": str(tmp_path / "missing.json")})
    assert not ok
    assert details["index"]["status"] == "error"
