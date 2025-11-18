from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import pytest


def _make_doc(path: Path, generated_at: str) -> None:
    doc = {
        "meta": {"generated_at": generated_at, "version": "v1"},
        "witness": {},
        "usage": {},
        "rating": {"subtotal": 0.1},
        "quota": {},
        "budget": {},
        "anomaly": {},
        "integrity": {},
    }
    core = {
        "meta": doc["meta"],
        "witness": doc["witness"],
        "usage": doc["usage"],
        "rating": doc["rating"],
        "quota": doc["quota"],
        "budget": doc["budget"],
        "anomaly": doc["anomaly"],
    }
    digest = hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    doc["integrity"]["signature_sha256"] = digest
    path.write_text(json.dumps(doc), encoding="utf-8")


@pytest.mark.skipif(platform.system().lower().startswith("win"), reason="bash required")
def test_gc_objectlock_dr_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    evdir = tmp_path / "evidence"
    evdir.mkdir()
    _make_doc(evdir / "one.json", "2025-01-01T00:00:00Z")
    _make_doc(evdir / "two.json", "2025-01-02T00:00:00Z")

    index_path = tmp_path / "index.json"
    from apps.obs.evidence.indexer import write_index

    write_index(str(evdir), str(index_path))

    monkeypatch.setenv("DECISIONOS_EVIDENCE_DIR", str(evdir))
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(index_path))
    monkeypatch.setenv("DECISIONOS_S3_MODE", "stub")
    monkeypatch.setenv("DECISIONOS_S3_STUB_ROOT", str(tmp_path / "s3_stub"))
    monkeypatch.setenv("DECISIONOS_S3_BUCKET", "dec-ev")
    monkeypatch.setenv("DECISIONOS_S3_PREFIX", "evidence/")
    monkeypatch.setenv("DECISIONOS_S3_DRY_RUN", "0")
    monkeypatch.setenv("DECISIONOS_S3_UPLOAD_ONLY_LOCKED", "0")

    from jobs.evidence_objectlock import main as upload

    upload()

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps({"include_globs": ["*.json"]}), encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_DR_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("DECISIONOS_DR_DEST", str(tmp_path / "restore"))
    monkeypatch.setenv("DECISIONOS_DR_REPORT_PATH", str(tmp_path / "reports" / "restore-report.json"))
    monkeypatch.setenv("DECISIONOS_DR_DRY_RUN", "0")

    from jobs.dr_restore import main as restore

    restore()

    assert (tmp_path / "restore" / "one.json").exists()
    assert (tmp_path / "restore" / "two.json").exists()
