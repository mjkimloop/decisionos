import time

import pytest
from fastapi.testclient import TestClient

from apps.judge.replay_plugins import ReplayStoreABC, SQLiteReplayStore
from apps.judge.server import create_app, _key_loader

pytestmark = [pytest.mark.gate_aj]


class FailingReplayStore(ReplayStoreABC):
    def seen_or_insert(self, key_id: str, nonce: str, ts_epoch: int) -> bool:
        return False

    def health_check(self) -> tuple[bool, str]:
        return False, "redis:down"


def _set_keys(monkeypatch, payload: str) -> None:
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", payload)
    _key_loader.force_reload()


def test_readyz_success(monkeypatch):
    _set_keys(monkeypatch, '[{"key_id":"k1","secret":"hex:11","state":"active"}]')
    app = create_app(replay_store=SQLiteReplayStore(path=":memory:"))
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["keys"]["key_count"] == 1


def test_readyz_stale_keys(monkeypatch):
    _set_keys(monkeypatch, '[{"key_id":"k1","secret":"hex:11","state":"active"}]')
    monkeypatch.setenv("DECISIONOS_JUDGE_KEY_GRACE_SEC", "1")
    # Force staleness
    _key_loader._loaded_at = time.time() - 10
    app = create_app(replay_store=SQLiteReplayStore(path=":memory:"))
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["checks"]["keys"]["status"] in {"stale", "error"}


def test_readyz_replay_store_failure(monkeypatch):
    _set_keys(monkeypatch, '[{"key_id":"k1","secret":"hex:11","state":"active"}]')
    app = create_app(replay_store=FailingReplayStore())
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
    body = resp.json()["detail"]
    assert body["checks"]["replay_store"]["status"].startswith("redis:")
