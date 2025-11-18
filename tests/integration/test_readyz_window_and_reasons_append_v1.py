from fastapi.testclient import TestClient

from apps.judge.server import create_app


def test_readyz_window_and_reasons_append(monkeypatch):
    monkeypatch.setenv("DECISIONOS_READY_FAIL_CLOSED", "0")
    app = create_app()
    client = TestClient(app)
    resp = client.get("/readyz", params={"window": 60, "explain": 1})
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert data.get("window") == 60
    assert "checks" in data
    assert isinstance(data.get("checks"), dict)
    assert "reason_codes" in data
    assert isinstance(data["reason_codes"], list)
