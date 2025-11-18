import importlib
import time

import pytest
from fastapi.testclient import TestClient

from apps.judge.replay_plugins import ReplayStoreABC, SQLiteReplayStore
import apps.judge.server as judge_server

pytestmark = [pytest.mark.gate_aj]


class FailingReplayStore(ReplayStoreABC):
    def seen_or_insert(self, key_id: str, nonce: str, ts_epoch: int) -> bool:
        return False

    def health_check(self) -> tuple[bool, str]:
        return False, "redis:down"


def _set_keys(monkeypatch, payload: str) -> None:
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", payload)
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run")
    judge_server._key_loader.force_reload()


def _reload_server():
    global judge_server
    judge_server = importlib.reload(judge_server)


def test_readyz_success(monkeypatch):
    _reload_server()
    _set_keys(monkeypatch, '[{"key_id":"k1","secret":"hex:11","state":"active"}]')
    assert judge_server._key_loader.info().get("key_count") == 1
    app = judge_server.create_app(replay_store=SQLiteReplayStore(path=":memory:"))
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["keys"]["key_count"] == 1


def test_readyz_stale_keys(monkeypatch):
    _reload_server()
    _set_keys(monkeypatch, '[{"key_id":"k1","secret":"hex:11","state":"active"}]')
    monkeypatch.setenv("DECISIONOS_JUDGE_KEY_GRACE_SEC", "1")
    # Force staleness
    judge_server._key_loader._loaded_at = time.time() - 10
    app = judge_server.create_app(replay_store=SQLiteReplayStore(path=":memory:"))
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503, resp.text
    detail = resp.json()
    assert detail["checks"]["keys"]["status"] in {"stale", "error", "missing"}


def test_readyz_replay_store_failure(monkeypatch):
    _reload_server()
    _set_keys(monkeypatch, '[{"key_id":"k1","secret":"hex:11","state":"active"}]')
    app = judge_server.create_app(replay_store=FailingReplayStore())
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["checks"]["replay_store"]["status"].startswith("unhealthy") or body["checks"]["replay_store"]["status"].startswith("error")
