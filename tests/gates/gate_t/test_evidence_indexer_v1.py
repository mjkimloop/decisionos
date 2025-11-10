import json
from pathlib import Path

import pytest

from apps.obs.evidence.indexer import scan_evidence_dir

pytestmark = [pytest.mark.gate_t]


def _make_evidence(path: Path) -> None:
    payload = {
        "meta": {"version": "vX", "tenant": "tenant-a", "generated_at": "2025-01-01T00:00:00Z"},
        "witness": {},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {},
        "anomaly": {},
        "integrity": {"signature_sha256": ""},
    }
    core = {key: payload[key] for key in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
    payload["integrity"]["signature_sha256"] = hashlib_sha(core)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def hashlib_sha(obj: dict) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    import hashlib

    return hashlib.sha256(data).hexdigest()


def test_scan_evidence_dir_marks_valid_files(tmp_path):
    ev = tmp_path / "evidence.json"
    _make_evidence(ev)
    index = scan_evidence_dir(str(tmp_path))
    assert index["summary"]["count"] == 1
    assert index["files"][0]["tampered"] is False


def test_scan_evidence_dir_marks_missing_blocks(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    index = scan_evidence_dir(str(tmp_path))
    assert index["files"][0]["tampered"] is True
