from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.catalog import indexer
from apps.gateway.main import app


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_gate_p_catalog_lineage_products_flow():
    indexer.clear()
    dataset_id = f"dataset_gatep_{uuid4().hex[:6]}"
    product_name = f"product_gatep_{uuid4().hex[:6]}"
    # Catalog creation
    create_payload = {
        "id": dataset_id,
        "name": "Gate-P Revenue Dataset",
        "type": "dataset",
        "domain": "finance",
        "description": "Revenue metrics per branch",
        "owner": "finops",
        "sensitivity": "internal",
        "tags": ["revenue", "monthly"],
        "fields": [
            {"name": "branch_id", "type": "string", "description": "branch code"},
            {"name": "total_revenue", "type": "decimal", "description": "total revenue for period"},
        ],
    }
    resp = client.post("/api/v1/catalog/items", headers=HEADERS, json=create_payload)
    assert resp.status_code == 201, resp.text

    resp = client.get("/api/v1/catalog/assets", headers=HEADERS, params={"type": "dataset", "domain": "finance"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(item["id"] == dataset_id for item in items)

    resp = client.get(f"/api/v1/catalog/datasets/{dataset_id}", headers=HEADERS)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["fields"][1]["name"] == "total_revenue"

    resp = client.get(
        "/api/v1/search",
        headers=HEADERS,
        params={"q": "revenue", "scope": "field"},
    )
    assert resp.status_code == 200
    assert any(result["id"] == dataset_id for result in resp.json()["results"])

    # Lineage ingestion
    lineage_payload = {
        "dataset": dataset_id,
        "edges": [
            {
                "source_dataset": dataset_id,
                "source_field": "total_revenue",
                "target_dataset": f"{dataset_id}_dashboard",
                "target_field": "revenue_total",
                "transformation": "sum(amount)",
                "confidence": 0.92,
            },
            {
                "source_dataset": dataset_id,
                "source_field": "branch_id",
                "target_dataset": f"{dataset_id}_dashboard",
                "target_field": "branch_id",
                "transformation": "identity",
            },
        ],
    }
    resp = client.post("/api/v1/lineage/edges", headers=HEADERS, json=lineage_payload)
    assert resp.status_code == 202
    assert resp.json()["ingested"] == len(lineage_payload["edges"])

    graph_resp = client.get(
        "/api/v1/lineage/graph",
        headers=HEADERS,
        params={"dataset": dataset_id, "depth": 2},
    )
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert f"{dataset_id}_dashboard" in graph_data["nodes"]
    assert any(edge["target_dataset"] == f"{dataset_id}_dashboard" for edge in graph_data["forward"])

    impact_resp = client.get(
        "/api/v1/lineage/impact",
        headers=HEADERS,
        params={"dataset": dataset_id, "field": "total_revenue"},
    )
    assert impact_resp.status_code == 200
    impact_data = impact_resp.json()
    assert any(entry["dataset"] == f"{dataset_id}_dashboard" for entry in impact_data["impacted"])

    # Product lifecycle
    product_spec = {
        "name": product_name,
        "version": "1.0.0",
        "owner": "finops",
        "input_datasets": [dataset_id],
        "transforms": ["aggregate_revenue"],
        "slas": {"freshness_hours": 6},
        "publish": [{"kind": "s3_parquet", "params": {"bucket": "demo-bucket", "prefix": product_name}}],
        "contracts": {"output_contract": "schemas/revenue_product.json"},
    }
    resp = client.post("/api/v1/products/register", headers=HEADERS, json=product_spec)
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/products/publish",
        headers=HEADERS,
        json={"name": product_name, "version": "1.0.0"},
    )
    assert resp.status_code == 200
    publish_data = resp.json()
    assert publish_data["status"] == "published"
    assert publish_data["manifest"]["product"] == product_name

    list_resp = client.get("/api/v1/products/list", headers=HEADERS)
    assert list_resp.status_code == 200
    assert any(item["name"] == product_name for item in list_resp.json()["products"])

