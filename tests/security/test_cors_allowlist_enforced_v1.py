# tests/security/test_cors_allowlist_enforced_v1.py
"""
Security test: CORS allowlist enforcement (v0.5.11u-5).

Validates:
- Production requires explicit allowlist (no wildcard)
- Development has safe defaults (localhost)
- Allowlist parsing and validation
"""
from __future__ import annotations

import os
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


def test_prod_rejects_wildcard_cors(monkeypatch):
    """Production must reject wildcard CORS."""
    monkeypatch.setenv("DECISIONOS_ENV", "prod")
    monkeypatch.setenv("DECISIONOS_CORS_ALLOWLIST", "*")

    from apps.gateway.security.cors import attach_strict_cors

    app = FastAPI()

    with pytest.raises(RuntimeError, match="CORS allowlist must be explicit in production"):
        attach_strict_cors(app)


def test_prod_rejects_empty_cors(monkeypatch):
    """Production must reject empty CORS allowlist."""
    monkeypatch.setenv("DECISIONOS_ENV", "prod")
    monkeypatch.setenv("DECISIONOS_CORS_ALLOWLIST", "")

    from apps.gateway.security.cors import attach_strict_cors

    app = FastAPI()

    with pytest.raises(RuntimeError, match="CORS allowlist must be explicit in production"):
        attach_strict_cors(app)


def test_prod_accepts_explicit_allowlist(monkeypatch):
    """Production accepts explicit allowlist."""
    monkeypatch.setenv("DECISIONOS_ENV", "prod")
    monkeypatch.setenv("DECISIONOS_CORS_ALLOWLIST", "https://app.example.com")

    from apps.gateway.security.cors import attach_strict_cors

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"pong": True}

    # Should not raise
    attach_strict_cors(app)

    # Test CORS behavior
    client = TestClient(app)

    # Allowed origin
    r = client.get("/ping", headers={"Origin": "https://app.example.com"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://app.example.com"

    # Disallowed origin (CORS middleware blocks)
    r2 = client.get("/ping", headers={"Origin": "https://evil.com"})
    assert r2.status_code == 200  # Request succeeds
    # But no CORS header (browser would block)
    assert r2.headers.get("access-control-allow-origin") is None


def test_dev_defaults_to_localhost(monkeypatch):
    """Development defaults to localhost origins."""
    monkeypatch.setenv("DECISIONOS_ENV", "dev")
    monkeypatch.delenv("DECISIONOS_CORS_ALLOWLIST", raising=False)

    from apps.gateway.security.cors import attach_strict_cors

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"pong": True}

    attach_strict_cors(app)

    client = TestClient(app)

    # Localhost should be allowed
    r = client.get("/ping", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_allowlist_parsing_comma_separated(monkeypatch):
    """Allowlist parsing supports comma-separated values."""
    monkeypatch.setenv("DECISIONOS_ENV", "staging")
    monkeypatch.setenv(
        "DECISIONOS_CORS_ALLOWLIST", "https://app.example.com,https://console.example.com"
    )

    from apps.gateway.security.cors import attach_strict_cors

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"pong": True}

    attach_strict_cors(app)

    client = TestClient(app)

    # Both origins should be allowed
    r1 = client.get("/ping", headers={"Origin": "https://app.example.com"})
    assert r1.headers.get("access-control-allow-origin") == "https://app.example.com"

    r2 = client.get("/ping", headers={"Origin": "https://console.example.com"})
    assert r2.headers.get("access-control-allow-origin") == "https://console.example.com"


def test_cors_exposes_custom_headers(monkeypatch):
    """CORS should expose custom headers (ETag, X-Delta-Base-ETag, etc.)."""
    monkeypatch.setenv("DECISIONOS_ENV", "dev")

    from apps.gateway.security.cors import attach_strict_cors

    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"ok": True}

    attach_strict_cors(app)

    client = TestClient(app)

    # Preflight request (OPTIONS)
    r = client.options(
        "/test",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "etag",
        },
    )

    # Should expose custom headers
    exposed = r.headers.get("access-control-expose-headers", "")
    assert "ETag" in exposed or "etag" in exposed.lower()
    assert "X-Delta-Base-ETag" in exposed or "x-delta-base-etag" in exposed.lower()
