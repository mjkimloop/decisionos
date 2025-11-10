from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.onboarding import service
from apps.docs_builder.builder import render_template, generate_bundle


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_signup_bootstrap_and_public_apis(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DEFAULT_STORE", tmp_path)

    signup_payload = {
        "email": "founder@example.com",
        "company": "Example Labs",
        "plan": "growth",
        "notes": "demo",
    }
    res = client.post("/api/v1/onboarding/signup", json=signup_payload, headers=HEADERS)
    assert res.status_code == 201
    signup_id = res.json()["id"]

    listing = client.get("/api/v1/onboarding/signups", headers=HEADERS)
    assert listing.status_code == 200
    assert any(item["id"] == signup_id for item in listing.json().get("items", []))

    bootstrap_payload = {
        "signup_id": signup_id,
        "org_name": "Example Org",
        "project_name": "Loan Pilot",
        "region": "region-a",
    }
    boot = client.post("/api/v1/onboarding/bootstrap", json=bootstrap_payload, headers=HEADERS)
    assert boot.status_code == 200
    body = boot.json()
    assert body["org_id"].startswith("org-")
    assert body["api_key"]

    status = client.get("/api/v1/status", headers=HEADERS)
    support = client.get("/api/v1/support", headers=HEADERS)
    pricing = client.get("/api/v1/pricing", headers=HEADERS)
    assert status.status_code == support.status_code == pricing.status_code == 200
    assert "plans" in pricing.json()


def test_docs_builder_bundle(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "welcome.tpl").write_text("Hello {name}!", encoding="utf-8")
    (template_dir / "plan.tpl").write_text("Plan: {plan}", encoding="utf-8")

    output_dir = tmp_path / "output"
    generate_bundle(template_dir, {"name": "Ada", "plan": "Growth"}, output_dir)

    content = (output_dir / "welcome.md").read_text(encoding="utf-8")
    assert "Ada" in content

    single = render_template(template_dir / "plan.tpl", {"plan": "Trial"}, output_dir / "single.md")
    assert "Trial" in single
