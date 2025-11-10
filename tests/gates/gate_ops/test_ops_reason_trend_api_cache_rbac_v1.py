import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from apps.obs.evidence.indexer import write_index
from apps.ops.api.cache import cache
from apps.ops.api.server import app
from apps.policy import pep

pytestmark = [pytest.mark.gate_t]


def _set_scope(monkeypatch, value: str) -> None:
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", value)
    pep._allowed.cache_clear()


def _prepare_env(tmp_path, monkeypatch):
    cache.clear()
    var_dir = tmp_path / "var" / "evidence"
    var_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return var_dir


def _write_evidence(path, generated_at: str) -> None:
    payload = {
        "meta": {"generated_at": generated_at, "tenant": "t1"},
        "witness": {},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {},
        "anomaly": {},
        "integrity": {"signature_sha256": "placeholder"},
        "judges": [{"reasons": [{"code": "perf.p95_over"}]}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_etag_and_304(tmp_path, monkeypatch):
    _prepare_env(tmp_path, monkeypatch)
    _set_scope(monkeypatch, "ops:read")

    client = TestClient(app)
    first = client.get("/ops/reason-trend/card?days=7&topK=2")
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag

    second = client.get(
        "/ops/reason-trend/card?days=7&topK=2",
        headers={"If-None-Match": etag},
    )
    assert second.status_code == 304
    assert second.headers.get("ETag") == etag
    assert "Cache-Control" in second.headers
    assert "Surrogate-Control" in second.headers
    assert "Last-Modified" in second.headers


def test_rbac_forbidden(tmp_path, monkeypatch):
    _prepare_env(tmp_path, monkeypatch)
    _set_scope(monkeypatch, "")

    client = TestClient(app)
    response = client.get("/ops/reason-trend/card?days=7&topK=2")
    assert response.status_code == 403


def test_etag_changes_after_index_update(tmp_path, monkeypatch):
    var_dir = _prepare_env(tmp_path, monkeypatch)
    _set_scope(monkeypatch, "ops:read")

    evidence = var_dir / "evidence-a.json"
    _write_evidence(evidence, "2025-11-10T00:00:00Z")
    write_index(str(var_dir))

    client = TestClient(app)
    first = client.get("/ops/reason-trend")
    assert first.status_code == 200
    etag_old = first.headers.get("ETag")
    last_modified_old = first.headers.get("Last-Modified")

    _write_evidence(evidence, "2025-11-11T00:00:00Z")
    future = time.time() + 5
    os.utime(evidence, (future, future))
    write_index(str(var_dir))

    second = client.get("/ops/reason-trend", headers={"If-None-Match": etag_old})
    assert second.status_code == 200
    assert second.headers.get("ETag") != etag_old
    assert second.headers.get("Last-Modified") != last_modified_old
