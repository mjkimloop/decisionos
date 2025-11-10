from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.packs.validator import load_pack_file


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def _sample_spec_json() -> dict:
    spec = load_pack_file(Path("packages/packs/lending_pack_v1.yaml"))
    return spec.model_dump(mode="json")


def test_packs_list_and_load():
    listing = client.get("/api/v1/packs", headers=HEADERS)
    assert listing.status_code == 200
    items = listing.json().get("items", [])
    assert any(item.get("identifier", "").startswith("lending_pack") for item in items)

    pack = client.get("/api/v1/packs/lending_pack_v1", headers=HEADERS)
    assert pack.status_code == 200
    body = pack.json()
    assert body.get("meta", {}).get("name") == "lending_pack"


def test_packs_validate_and_simulate():
    payload = {"pack": _sample_spec_json()}
    validate_resp = client.post("/api/v1/packs/validate", headers=HEADERS, json=payload)
    assert validate_resp.status_code == 200
    assert validate_resp.json().get("valid") is True

    rows = [
        {
            "org_id": "demo-tenant",
            "converted": 0,
            "credit_score": 640,
            "dti": 0.42,
            "income_verified": True,
            "employment_type": "salaried",
            "region": "SEO",
        },
        {
            "org_id": "demo-tenant",
            "converted": 1,
            "credit_score": 720,
            "dti": 0.28,
            "income_verified": True,
            "employment_type": "salaried",
            "region": "PUS",
        },
    ]
    sim_resp = client.post(
        "/api/v1/packs/simulate",
        headers=HEADERS,
        json={"pack": payload["pack"], "rows": rows, "label_key": "converted"},
    )
    assert sim_resp.status_code == 200
    data = sim_resp.json()
    assert data.get("n") == 2
    assert "lead_triage" in data.get("contracts", {})
