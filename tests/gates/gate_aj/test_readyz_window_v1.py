import os
from starlette.testclient import TestClient

from apps.judge.server import app


def test_readyz_window_and_codes(monkeypatch):
    for k in ["DECISIONOS_READY_KEYS", "DECISIONOS_READY_REPLAY", "DECISIONOS_READY_STORE", "DECISIONOS_READY_CLOCK"]:
        monkeypatch.setenv(k, "ok")
    c = TestClient(app)
    r1 = c.get("/readyz?window=5&explain=1")
    assert r1.status_code == 200
    js1 = r1.json()
    assert js1["status"] == "ready"
    assert js1["window"]["samples"] >= 1

    monkeypatch.setenv("DECISIONOS_READY_KEYS", "fail")
    r2 = c.get("/readyz?window=5&explain=1")
    assert r2.status_code == 503
    js2 = r2.json()
    assert js2["status"] == "degraded"
    assert js2["window"]["last"]["reasons"]
