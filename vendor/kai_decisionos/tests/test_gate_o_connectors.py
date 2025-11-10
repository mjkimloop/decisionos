from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.gateway.main import app


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}
ROOT = Path(__file__).resolve().parents[1]


def test_connectors_contracts_pipeline_quality():
    # connectors list
    resp = client.get("/api/v1/connectors", headers=HEADERS)
    assert resp.status_code == 200
    assert "csv" in resp.json()

    csv_path = ROOT / "packages" / "samples" / "offline_eval.sample.csv"
    resp = client.post(
        "/api/v1/connectors/test",
        headers=HEADERS,
        json={"name": "csv", "params": {"path": str(csv_path)}},
    )
    assert resp.status_code == 200
    assert resp.json()["sample"]
    catalog_body = {
        "id": "dataset_leads",
        "name": "Leads Dataset",
        "description": "Primary leads feed",
        "owner": "data-team",
        "tags": ["leads", "sales"],
        "sensitivity": "internal",
    }
    create = client.post("/api/v1/catalog/items", headers=HEADERS, json=catalog_body)
    assert create.status_code == 201

    listing = client.get("/api/v1/catalog/assets", headers=HEADERS, params={"type": "dataset"})
    assert listing.status_code == 200
    assets = listing.json()["items"]
    assert any(item["id"] == "dataset_leads" for item in assets)

    fetched = client.get("/api/v1/catalog/datasets/dataset_leads", headers=HEADERS)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Leads Dataset"

    search = client.get(
        "/api/v1/search",
        headers=HEADERS,
        params={"q": "leads"},
    )
    assert search.status_code == 200
    assert search.json()["results"]

    contract_path = ROOT / "packages" / "contracts" / "lead_triage.contract.json"
    validate = client.post(
        "/api/v1/contracts/validate",
        headers=HEADERS,
        json={
            "contract_path": str(contract_path),
            "payload": {"id": "demo", "payload": {}},
            "kind": "input",
        },
    )
    assert validate.status_code == 200
    assert "valid" in validate.json()

    compare = client.get(
        "/api/v1/contracts/compare",
        headers=HEADERS,
        params={"base": "v0.1.0", "target": "v0.1.1"},
    )
    assert compare.status_code == 200

    pipeline = client.post(
        "/api/v1/pipelines/run",
        headers=HEADERS,
        json={"records": [{"id": "abc", "income": " 1000 ", "email": "user@example.com"}]},
    )
    assert pipeline.status_code == 200
    assert pipeline.json()["n"] == 1

    quality = client.post(
        "/api/v1/quality/metrics",
        headers=HEADERS,
        json={"records": [{"id": "abc", "score": 10}, {"id": "def", "score": None}], "keys": ["score"]},
    )
    assert quality.status_code == 200
    assert "metrics" in quality.json()
