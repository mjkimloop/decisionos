import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.judge.crypto import hmac_sign_canonical
from scripts.ci import validate_artifacts as va


def _write_upload(path: Path, *, applied: bool) -> None:
    payload = {
        "mode": "stub",
        "counts": {"uploaded": 1, "skipped": 0, "failed": 0},
        "object_lock": {"applied": applied, "mode": "COMPLIANCE" if applied else "GOVERNANCE"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_pii_required_in_prod(monkeypatch):
    monkeypatch.setenv("DECISIONOS_MODE", "prod")
    monkeypatch.delenv("DECISIONOS_PII_ENABLE", raising=False)
    with pytest.raises(SystemExit):
        va.assert_pii_on_when_prod(dict(os.environ))


def test_verify_signed_policy_mismatch(tmp_path, monkeypatch):
    file = tmp_path / "policy.signed.json"
    payload = {"policy": "dummy", "version": "1"}
    file.write_text(json.dumps({"payload": payload, "signature": {"key_id": "k1", "hmac_sha256": "deadbeef"}}), encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", '[{"key_id":"k1","secret":"policy-secret","state":"active"}]')
    with pytest.raises(SystemExit):
        va.verify_signed_policy(str(file))


def test_verify_signed_policy_passes(tmp_path, monkeypatch):
    payload = {"policy": "dummy-ok", "version": "2"}
    secret = "policy-secret"
    signature = hmac_sign_canonical(payload, secret)
    file = tmp_path / "good-policy.signed.json"
    file.write_text(json.dumps({"payload": payload, "signature": {"key_id": "k1", "hmac_sha256": signature}}), encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", '[{"key_id":"k1","secret":"policy-secret","state":"active"}]')
    va.verify_signed_policy(str(file))


def test_objectlock_enforce_flag_via_cli(tmp_path):
    upload = tmp_path / "upload.json"
    _write_upload(upload, applied=False)
    cmd = [
        sys.executable,
        "-m",
        "scripts.ci.validate_artifacts",
        "--upload",
        str(upload),
        "--objectlock-enforce",
    ]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode != 0
