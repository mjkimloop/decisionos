from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _write_doc(path: Path, *, locked: bool) -> None:
    meta = {
        "version": "vX",
        "generated_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
    }
    if locked:
        meta["locked_at"] = meta["generated_at"]
    doc = {
        "meta": meta,
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
    sig = hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    doc["integrity"]["signature_sha256"] = sig
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_objectlock_job_uploads_stub_files(tmp_path, monkeypatch):
    evdir = tmp_path / "evidence"
    evdir.mkdir()
    _write_doc(evdir / "locked.locked.json", locked=True)
    _write_doc(evdir / "wip.json", locked=False)

    report_path = tmp_path / "reports" / "objectlock-report.json"

    monkeypatch.setenv("DECISIONOS_EVIDENCE_DIR", str(evdir))
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(tmp_path / "index.json"))
    monkeypatch.setenv("DECISIONOS_OBJECTLOCK_REPORT", str(report_path))
    monkeypatch.setenv("DECISIONOS_S3_MODE", "stub")
    monkeypatch.setenv("DECISIONOS_S3_STUB_ROOT", str(tmp_path / "s3_stub"))
    monkeypatch.setenv("DECISIONOS_S3_BUCKET", "dec-ev")
    monkeypatch.setenv("DECISIONOS_S3_PREFIX", "evidence/")
    monkeypatch.setenv("DECISIONOS_S3_UPLOAD_ONLY_LOCKED", "0")
    monkeypatch.setenv("DECISIONOS_S3_DRY_RUN", "0")

    from jobs.evidence_objectlock import main as run

    run()

    locked_path = tmp_path / "s3_stub" / "dec-ev" / "evidence" / "locked.locked.json"
    wip_path = tmp_path / "s3_stub" / "dec-ev" / "evidence" / "wip.json"
    assert locked_path.exists()
    assert Path(f"{locked_path}.lock.json").exists()
    assert wip_path.exists()
    assert Path(f"{wip_path}.lock.json").exists()

    rep = json.loads(report_path.read_text(encoding="utf-8"))
    assert rep["counts"]["uploaded"] == 2
    assert rep["counts"]["failed"] == 0
    assert rep["policy"]["only_locked"] is False
