# tests/contracts/test_router_response_contract_v2.py
"""
Response contract snapshot tests for major routers (v0.5.11u-15b).

Ensures API response schemas remain stable during Pydantic v2 migration.
"""
from __future__ import annotations

import json
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient


def normalize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize response for snapshot comparison.

    Removes volatile fields like timestamps, while preserving structure.
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            # Skip volatile timestamp fields
            if k in ("generated_at", "timestamp", "last_modified", "ts"):
                result[k] = "<TIMESTAMP>"
            elif k == "_meta" and isinstance(v, dict):
                # Normalize metadata paths
                result[k] = {
                    mk: ("<PATH>" if "path" in mk else mv)
                    for mk, mv in v.items()
                }
            else:
                result[k] = normalize_response(v)
        return result
    elif isinstance(data, list):
        return [normalize_response(item) for item in data]
    else:
        return data


@pytest.fixture
def gateway_client(tmp_path, monkeypatch):
    """Create test client with minimal evidence index."""
    # Setup test evidence index
    index_path = tmp_path / "evidence_index.json"
    evidence_data = {
        "generated_at": "2025-11-19T00:00:00Z",
        "buckets": [
            {
                "ts": "2025-11-19T10:00:00Z",
                "reasons": {
                    "PERF_DEGRADATION": 10,
                    "ERROR_RATE_HIGH": 5,
                    "LATENCY_SPIKE": 3,
                },
            },
            {
                "ts": "2025-11-18T10:00:00Z",
                "reasons": {
                    "PERF_DEGRADATION": 8,
                    "ERROR_RATE_HIGH": 7,
                },
            },
        ],
    }
    index_path.write_text(json.dumps(evidence_data), encoding="utf-8")

    # Configure environment
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(index_path))
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    monkeypatch.setenv("DECISIONOS_COMPRESS_ENABLE", "0")  # Disable compression for testing

    # Import app after monkeypatch
    from apps.gateway.main import app

    return TestClient(app)


def test_cards_reason_trends_response_structure(gateway_client):
    """
    Test /ops/cards/reason-trends response structure.

    Validates:
    - Top-level fields present
    - groups structure
    - buckets array structure
    - top_reasons array structure
    - summary fields
    - _meta fields
    """
    resp = gateway_client.get(
        "/ops/cards/reason-trends?period=7d&bucket=day",
        headers={"X-Scopes": "ops:read"},
    )

    assert resp.status_code == 200

    data = resp.json()
    normalized = normalize_response(data)

    # Verify top-level structure
    assert "data" in normalized
    assert "delta" in normalized
    assert "_meta" in normalized

    # Verify data structure
    data_obj = normalized["data"]
    assert "generated_at" in data_obj
    assert "period" in data_obj
    assert "bucket" in data_obj
    assert "groups" in data_obj
    assert "buckets" in data_obj
    assert "top_reasons" in data_obj
    assert "summary" in data_obj
    assert "_meta" in data_obj

    # Verify groups structure
    assert isinstance(data_obj["groups"], dict)
    for group_name, group_data in data_obj["groups"].items():
        assert "score" in group_data
        assert "count" in group_data
        assert "weight" in group_data
        assert isinstance(group_data["score"], (int, float))
        assert isinstance(group_data["count"], (int, float))

    # Verify buckets structure
    assert isinstance(data_obj["buckets"], list)
    for bucket in data_obj["buckets"]:
        assert "ts" in bucket
        assert "bucket" in bucket
        assert "groups" in bucket
        assert isinstance(bucket["groups"], dict)

    # Verify top_reasons structure
    assert isinstance(data_obj["top_reasons"], list)
    for reason in data_obj["top_reasons"]:
        assert "reason" in reason
        assert "score" in reason
        assert "count" in reason
        assert isinstance(reason["reason"], str)
        assert isinstance(reason["score"], (int, float))
        assert isinstance(reason["count"], int)

    # Verify summary structure
    summary = data_obj["summary"]
    assert "total_events" in summary
    assert "unique_reasons" in summary
    assert isinstance(summary["total_events"], (int, float))
    assert isinstance(summary["unique_reasons"], int)

    # Verify _meta structure
    meta = data_obj["_meta"]
    assert "index_path" in meta
    assert "weights_path" in meta


def test_cards_etag_headers_present(gateway_client):
    """Test Cards API includes ETag and caching headers."""
    resp = gateway_client.get(
        "/ops/cards/reason-trends",
        headers={"X-Scopes": "ops:read"},
    )

    assert resp.status_code == 200
    assert "ETag" in resp.headers
    assert "Cache-Control" in resp.headers
    assert "Vary" in resp.headers

    # Verify Vary includes critical headers
    vary_header = resp.headers["Vary"]
    assert "Accept-Encoding" in vary_header
    assert "X-Scopes" in vary_header or "Authorization" in vary_header


def test_cards_304_not_modified(gateway_client):
    """Test Cards API returns 304 with If-None-Match."""
    # First request to get ETag
    resp1 = gateway_client.get(
        "/ops/cards/reason-trends",
        headers={"X-Scopes": "ops:read"},
    )
    assert resp1.status_code == 200
    etag = resp1.headers["ETag"]

    # Second request with If-None-Match
    resp2 = gateway_client.get(
        "/ops/cards/reason-trends",
        headers={
            "X-Scopes": "ops:read",
            "If-None-Match": etag,
        },
    )

    assert resp2.status_code == 304
    assert resp2.headers["ETag"] == etag
    assert "Vary" in resp2.headers


def test_healthz_response_structure(gateway_client):
    """Test /healthz response structure."""
    resp = gateway_client.get("/healthz")

    assert resp.status_code == 200
    data = resp.json()

    assert "ok" in data
    assert isinstance(data["ok"], bool)
    assert data["ok"] is True


def test_cards_delta_field_types(gateway_client):
    """
    Test Cards API field types match schema.

    Ensures Pydantic v2 serialization doesn't change types.
    """
    resp = gateway_client.get(
        "/ops/cards/reason-trends?period=7d&bucket=day",
        headers={"X-Scopes": "ops:read"},
    )

    assert resp.status_code == 200
    data = resp.json()

    # Type checks
    assert isinstance(data, dict)
    assert isinstance(data.get("data"), dict)
    assert data.get("delta") is None or isinstance(data["delta"], dict)
    assert isinstance(data.get("_meta"), dict)

    data_obj = data["data"]
    assert isinstance(data_obj["period"], str)
    assert isinstance(data_obj["bucket"], str)
    assert isinstance(data_obj["groups"], dict)
    assert isinstance(data_obj["buckets"], list)
    assert isinstance(data_obj["top_reasons"], list)
    assert isinstance(data_obj["summary"], dict)


def test_cards_response_json_serializable(gateway_client):
    """Test Cards API response is valid JSON (no NaN, Inf, etc.)."""
    resp = gateway_client.get(
        "/ops/cards/reason-trends",
        headers={"X-Scopes": "ops:read"},
    )

    assert resp.status_code == 200

    # Should be valid JSON
    data = resp.json()
    json_str = json.dumps(data)

    # Re-parse to ensure no corruption
    reparsed = json.loads(json_str)
    assert reparsed == data

    # Verify no special float values (use word boundaries to avoid false positives)
    import re
    json_str_lower = json_str.lower()
    assert not re.search(r'\bnan\b', json_str_lower), "Found NaN in JSON"
    assert not re.search(r'\binf(inity)?\b', json_str_lower), "Found Infinity in JSON"
