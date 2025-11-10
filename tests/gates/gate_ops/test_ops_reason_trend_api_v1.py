import pytest
from fastapi.testclient import TestClient

from apps.ops.api.server import app

pytestmark = [pytest.mark.gate_t]


def test_ops_api_card_smoke(tmp_path, monkeypatch):
    # ensure aggregator points to a temp var/evidence directory
    var_dir = tmp_path / "var" / "evidence"
    var_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    client = TestClient(app)
    response = client.get("/ops/reason-trend/card?days=7&topK=3")
    assert response.status_code == 200
    body = response.json()
    assert "top" in body
    assert body["window_days"] == 7
