import importlib

import pytest
from starlette.testclient import TestClient

pytestmark = [pytest.mark.gate_aj]


def test_readyz_fail_closed(monkeypatch):
    monkeypatch.setenv("DECISIONOS_READY_FAIL_CLOSED", "1")
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "[]")
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run")
    import apps.judge.server as server

    importlib.reload(server)

    client = TestClient(server.app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
