from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _write_stub_file(root: Path, bucket: str, key: str, body: bytes) -> None:
    path = root / bucket / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    lock_path = Path(f"{path}.lock.json")
    lock_path.write_text(json.dumps({"mode": "GOVERNANCE"}), encoding="utf-8")


def _hash(body: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(body)
    return digest.hexdigest()


def test_dr_restore_stub(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stub_root = tmp_path / "s3_stub"
    body_a = b'{"meta":{"v":"1"}}'
    body_b = b'{"meta":{"v":"2"}}'
    _write_stub_file(stub_root, "dec-ev", "evidence/a.json", body_a)
    _write_stub_file(stub_root, "dec-ev", "evidence/b.json", body_b)

    index_path = tmp_path / "index.json"
    index_data = {
        "items": [
            {"path": "var/evidence/a.json", "sha256": _hash(body_a)},
            {"path": "var/evidence/b.json", "sha256": _hash(body_b)},
        ]
    }
    index_path.write_text(json.dumps(index_data), encoding="utf-8")

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps({"include_globs": ["*.json"], "verify_lock": True, "verify_sha": True}),
        encoding="utf-8",
    )

    report_path = tmp_path / "reports" / "restore-report.json"
    dest = tmp_path / "restore"

    monkeypatch.setenv("DECISIONOS_S3_MODE", "stub")
    monkeypatch.setenv("DECISIONOS_S3_STUB_ROOT", str(stub_root))
    monkeypatch.setenv("DECISIONOS_S3_BUCKET", "dec-ev")
    monkeypatch.setenv("DECISIONOS_S3_PREFIX", "evidence/")
    monkeypatch.setenv("DECISIONOS_DR_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("DECISIONOS_DR_DEST", str(dest))
    monkeypatch.setenv("DECISIONOS_DR_DRY_RUN", "0")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(index_path))
    monkeypatch.setenv("DECISIONOS_DR_REPORT_PATH", str(report_path))

    from jobs.dr_restore import main

    main()

    assert (dest / "a.json").exists()
    assert (dest / "b.json").exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["counts"]["restored"] == 2
    ok = [entry for entry in report["restored"] if entry.get("sha_ok") and entry.get("lock_ok")]
    assert len(ok) == 2
