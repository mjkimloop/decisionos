from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from apps.gateway.main import app
from apps.policy.store import STORE

client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}
DEFAULT_VERSION = "v1.0.0"
DEFAULT_APPROVER = "security-reviewer"


def _install_policy(name: str, bundle: str, version: str = DEFAULT_VERSION) -> None:
    resp = client.post(
        "/api/v1/policies/install",
        headers=HEADERS,
        json={
            "name": name,
            "bundle": bundle,
            "version": version,
            "approved_by": DEFAULT_APPROVER,
            "summary": "unit-test install",
        },
    )
    assert resp.status_code == 200, resp.text


@pytest.fixture(autouse=True)
def clear_store():
    STORE._policies.clear()  # type: ignore[attr-defined]
    yield
    STORE._policies.clear()  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def clear_tags():
    from apps.catalog.tags import clear_registry
    from apps.catalog.boundaries import clear_events

    clear_registry()
    clear_events()
    yield
    clear_registry()
    clear_events()


def test_policy_eval_and_apply():
    bundle = """
permit(read, subject, resource)
  when { subject.get('role') == 'admin' }
"""
    _install_policy("default", bundle)
    eval_resp = client.post(
        "/api/v1/policies/eval",
        headers=HEADERS,
        json={"subject": {"role": "admin"}, "action": "read", "resource": {}, "context": {}},
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["allow"] is True


def test_policy_metadata_persisted():
    bundle = """
permit(read, subject, resource)
  when { subject.get('role') == 'admin' }
"""
    _install_policy("meta-check", bundle, version="v2.3.4")
    list_resp = client.get("/api/v1/policies/list", headers=HEADERS)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "meta-check" in data
    assert data["meta-check"]["metadata"]["version"] == "v2.3.4"
    assert data["meta-check"]["metadata"]["approved_by"] == DEFAULT_APPROVER


def test_boundary_check_residency_violation():
    from apps.catalog.tags import tag_dataset

    tag_dataset("dataset_kr", {"residency": "KR"})
    resp = client.get(
        "/api/v1/boundaries/check",
        headers=HEADERS,
        params={"dataset": "dataset_kr", "org_id": "US:org-1"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"] == "residency_violation"
    assert "policy.override" in detail["required_controls"]


def test_boundary_check_success():
    from apps.catalog.tags import tag_dataset

    tag_dataset("dataset_us", {"residency": "US", "allowed_regions": ["US", "CA"], "controls": {"mask": {"email": "hash"}}})
    resp = client.get(
        "/api/v1/boundaries/check",
        headers=HEADERS,
        params={
            "dataset": "dataset_us",
            "org_id": "US:org-5",
            "target_region": "CA",
            "purpose": "analytics",
            "ticket_id": "CHG-101",
            "retention_days": 30,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tags"]["residency"] == "US"
    assert any(control.startswith("mask:") for control in body["enforced_controls"])


def test_boundary_alert_stream_records_events():
    from apps.catalog.tags import tag_dataset

    tag_dataset("dataset_strict", {"residency": "KR", "classification": "PII-S"})
    resp = client.get(
        "/api/v1/boundaries/check",
        headers=HEADERS,
        params={"dataset": "dataset_strict", "org_id": "US:org-9"},
    )
    assert resp.status_code == 403
    alerts = client.get("/api/v1/boundaries/alerts", headers=HEADERS)
    assert alerts.status_code == 200
    data = alerts.json()["items"]
    assert data and data[0]["dataset_id"] == "dataset_strict"
    assert data[0]["reason"] == "residency_mismatch"


def test_masking_and_tokenization():
    from apps.security.masking import mask_phone
    from apps.security.tokenization import tokenize, detokenize, inspect

    assert mask_phone("010-1234-5678").endswith("5678")
    token = tokenize("secret-value", metadata={"dataset_id": "sample"})
    assert detokenize(token) == "secret-value"
    meta = inspect(token)
    assert meta["metadata"]["dataset_id"] == "sample"


def test_policy_install_rejects_unsafe_expression():
    bundle = """
permit(read, subject, resource)
  when { subject.__class__ == 'ShouldFail' }
"""
    resp = client.post(
        "/api/v1/policies/install",
        headers=HEADERS,
        json={
            "name": "unsafe",
            "bundle": bundle,
            "version": DEFAULT_VERSION,
            "approved_by": DEFAULT_APPROVER,
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "dunder_attribute_not_allowed"


def test_tokenization_unknown_token_raises():
    from apps.security.tokenization import detokenize

    with pytest.raises(KeyError):
        detokenize("tok_unknown")


def test_sql_pep_masks_sensitive_rows():
    from apps.policy.pep.sql import enforce_sql
    from apps.catalog.tags import tag_dataset

    bundle = """
permit(read, subject, resource)
  when { subject.get('role') == 'admin' }
"""
    _install_policy("sql", bundle)
    tag_dataset(
        "dataset_users",
        {
            "classification": "PII",
            "controls": {"mask": {"email": "email", "phone": "phone", "ssn": "full"}},
        },
    )
    rows = [{"email": "user@example.com", "phone": "010-9999-8888", "ssn": "123-45-6789"}]
    masked_rows = enforce_sql(
        {"role": "admin"},
        {"dataset_id": "dataset_users", "classification": "PII"},
        "SELECT * FROM users",
        rows,
    )
    assert masked_rows[0]["email"].startswith("us")
    assert masked_rows[0]["phone"].endswith("8888")
    assert masked_rows[0]["ssn"].startswith("***")


def test_sql_tokenization_controls_apply():
    from apps.policy.pep.sql import enforce_sql
    from apps.catalog.tags import tag_dataset
    from apps.security.tokenization import detokenize

    bundle = """
permit(read, subject, resource)
  when { subject.get('role') == 'admin' }
"""
    _install_policy("sql-tok", bundle)
    tag_dataset(
        "dataset_sensitive",
        {"classification": "PII-S", "controls": {"tokenize": ["ssn"]}},
    )
    rows = [{"ssn": "987-65-4321"}]
    masked_rows = enforce_sql(
        {"role": "admin"},
        {"dataset_id": "dataset_sensitive", "classification": "PII-S"},
        "SELECT ssn FROM sensitive",
        rows,
    )
    token = masked_rows[0]["ssn"]
    assert token.startswith("tok_")
    assert detokenize(token) == "987-65-4321"


def test_pipeline_policy_guard_masks_records():
    from apps.policy.pep.rpc import enforce_rpc
    from apps.pipelines.service import run_pipeline
    from apps.catalog.tags import tag_dataset

    bundle = """
permit(read, subject, resource)
  when { subject.get('role') == 'admin' }
"""
    _install_policy("rpc", bundle)
    tag_dataset(
        "rpc_dataset",
        {"classification": "PII", "controls": {"mask": {"phone": "phone", "email": "email"}}},
    )

    def guard(record):
        return enforce_rpc(
            {"role": "admin"},
            {"dataset_id": "rpc_dataset", "classification": "PII"},
            {"action": "read"},
            record,
        )

    output = run_pipeline(
        [{"id": 1, "phone": "010-4321-0000", "email": "hello@example.com"}],
        steps=[],
        policy_guard=guard,
    )
    assert output[0]["phone"].endswith("0000")
    assert output[0]["email"].startswith("he")
