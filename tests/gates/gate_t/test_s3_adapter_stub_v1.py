from __future__ import annotations

import json
from pathlib import Path

from apps.common.s3_adapter import StubS3Adapter, select_adapter


def test_stub_adapter_respects_local_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DECISIONOS_S3_MODE", "stub")
    monkeypatch.setenv("DECISIONOS_S3_STUB_ROOT", str(tmp_path / "s3_stub"))
    adapter = select_adapter()
    assert isinstance(adapter, StubS3Adapter)

    payload = b"hello-evidence"
    resp = adapter.put_with_object_lock("bucket-x", "evidence/file.json", payload, retention_days=5)

    dst = tmp_path / "s3_stub" / "bucket-x" / "evidence" / "file.json"
    lock_path = Path(f"{dst}.lock.json")
    assert dst.read_bytes() == payload
    assert lock_path.exists()
    lock_meta = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock_meta["retention_days"] == 5
    assert resp.adapter == "stub"
    assert resp.bucket == "bucket-x"
    assert resp.key == "evidence/file.json"
    assert resp.url == "stub://bucket-x/evidence/file.json"
