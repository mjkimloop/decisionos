from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from apps.ext.sandbox.runner import SandboxRunner, SandboxViolation
from apps.ext.sandbox.limits import ResourceLimits
from apps.ext.signing.sign import sign_artifact
from apps.ext.registry.oci import REGISTRY, Artifact
from apps.gateway.main import app

client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_sandbox_enforces_resource_limits():
    runner = SandboxRunner()
    manifest = {"resources": {"mem_mb": 256}}
    with pytest.raises(SandboxViolation):
        runner.execute(lambda config, ctx: None, {"extension": "demo"}, manifest, limits=ResourceLimits(memory_mb=128))


def test_extension_install_flow(tmp_path: Path):
    REGISTRY._artifacts.clear()  # type: ignore[attr-defined]
    artifact_path = tmp_path / "demo-ext.tgz"
    artifact_path.write_bytes(b"artifact-bytes")
    ref = "ext:demo/demo:0.1.0"
    metadata = {"name": "demo", "version": "0.1.0", "channel": "private-beta"}
    REGISTRY.push(ref, Artifact(name="demo", version="0.1.0", channel="private-beta", path=str(artifact_path), metadata=metadata))
    signature = sign_artifact(artifact_path)

    install = client.post(
        "/api/v1/ext/install",
        headers=HEADERS,
        json={"org_id": "org-1", "artifact_ref": ref, "signature": signature},
    )
    assert install.status_code == 201, install.text

    enable = client.post(
        "/api/v1/ext/enable",
        headers=HEADERS,
        json={"org_id": "org-1", "name": "demo", "version": "0.1.0"},
    )
    assert enable.status_code == 200

    listing = client.get("/api/v1/ext/list", headers=HEADERS, params={"org_id": "org-1"})
    assert listing.status_code == 200
    assert listing.json()[0]["enabled"] is True


def test_webhook_signature_verification():
    timestamp = str(int(time.time()))
    secret = "hook-secret"
    body = yaml.safe_dump({"message": "hello"})
    signature = hmac.new(secret.encode("utf-8"), msg=(timestamp + "." + body).encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/v1/webhooks/deliver",
        headers=HEADERS,
        json={"event": "test", "headers": {"X-Ext-Signature": signature, "X-Ext-Timestamp": timestamp}, "payload": body, "secret": secret},
    )
    assert resp.status_code == 200

