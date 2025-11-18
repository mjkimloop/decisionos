import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.security.pii_middleware import PIIMiddleware

pytestmark = pytest.mark.gate_ops


def build_app():
    app = FastAPI()
    app.add_middleware(PIIMiddleware)

    @app.get("/echo")
    def echo(q: str):
        return {"message": q}

    return app


def test_pii_middleware_default_off(monkeypatch):
    app = build_app()
    client = TestClient(app)
    resp = client.get("/echo", params={"q": "test@example.com"})
    assert resp.json()["message"] == "test@example.com"


def test_pii_middleware_on(monkeypatch):
    monkeypatch.setenv("DECISIONOS_PII_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_PII_MASK_TOKEN", "[MASK]")
    app = build_app()
    client = TestClient(app)
    resp = client.get("/echo", params={"q": "test@example.com"})
    assert "[MASK]" in resp.json()["message"]
