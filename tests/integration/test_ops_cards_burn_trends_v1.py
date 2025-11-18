import json
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient


def _load_app():
    module_path = Path("apps/ops/api.py").resolve()
    spec = importlib.util.spec_from_file_location("ops_api_app", module_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module.app


def test_burn_trends_card(monkeypatch, tmp_path):
    report = {
        "generated_at": 170000,
        "overall": {"state": "ok", "window": "5m"},
        "windows": [
            {
                "name": "5m",
                "duration": 300,
                "state": "ok",
                "metrics": {"error_rate": {"burn": 1.0, "value": 0.01, "errors": 1, "total": 100}},
            }
        ],
    }
    report_path = tmp_path / "burn.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setenv("BURN_REPORT_PATH", str(report_path))
    monkeypatch.setenv("BURN_POLICY_PATH", "configs/slo/burn_policy.yaml")
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")

    app = _load_app()
    client = TestClient(app)
    response = client.get("/ops/cards/burn-trends?window=5m")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["windows"][0]["name"] == "5m"
