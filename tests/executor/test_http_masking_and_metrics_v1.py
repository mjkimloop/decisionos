import pytest

from apps.executor import plugins
from apps.executor.plugins import _mask_headers, _mask_json


def test_masking_utils():
    h = {"Authorization": "Bearer x", "X-Api-Key": "zzz", "X-Other": "ok"}
    m = _mask_headers(h)
    assert m["Authorization"] == "***"
    assert m["X-Other"] == "ok"
    j = {"password": "a", "data": "b"}
    masked = _mask_json(j)
    assert masked["password"] == "***"


def test_http_idempotent_retry_flag(monkeypatch):
    calls = {"n": 0}

    class FakeResp:
        status_code = 500
        headers = {}

        def json(self):
            return {"ok": True}

        @property
        def text(self):
            return "ok"

    def fake_request(self, method, url, headers=None, json=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise plugins.httpx.ConnectError("boom")  # type: ignore[attr-defined]
        return FakeResp()

    monkeypatch.setenv("DECISIONOS_EXEC_HTTP_TIMEOUT", "0.1")
    monkeypatch.setenv("DECISIONOS_EXEC_HTTP_RETRIES", "1")
    monkeypatch.setenv("DECISIONOS_EXEC_HTTP_RETRY_NON_IDEMPOTENT", "0")
    monkeypatch.setattr(plugins.httpx.Client, "request", fake_request)  # type: ignore[arg-type]

    with pytest.raises(Exception):
        plugins.http_call({"method": "POST", "url": "http://example", "json": {"a": 1}})

    calls["n"] = 0
    out = plugins.http_call({"method": "POST", "url": "http://example", "json": {"a": 1}, "idempotent": True})
    assert out["status_code"] == 500
    assert calls["n"] == 2
