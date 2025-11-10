from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.gateway.main import app

from scripts.rotate_manifests import rotate

client = TestClient(app)

HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin"}


def test_rotate_manifest_creates_file(tmp_path: Path):
    # ensure there is at least one decision to generate audit log
    payload = {"org_id": "orgA", "payload": {"credit_score": 710, "dti": 0.25, "income_verified": True}}
    r = client.post("/api/v1/decide/lead_triage", headers=HEADERS, json=payload)
    assert r.status_code == 200

    out = rotate()
    assert out.exists()
    data = out.read_text(encoding="utf-8")
    assert "anchor" in data and "ledger_path" in data
