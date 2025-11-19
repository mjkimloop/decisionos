import types

import pytest

from apps.switchboard.adapters import openai as oa


def test_openai_adapter_cost_fallback(monkeypatch):
    adapter = oa.OpenAIAdapter()
    adapter.max_cost_usd = 0.000001  # 강제 제한
    adapter.api_key = "dummy"
    monkeypatch.setattr(oa, "httpx", None)  # httpx 미존재 시에도 fallback
    out = adapter.generate("a" * 400)
    assert out["fallback_used"] is True
    assert out["reason"] in ("cost_exceeded", "missing_httpx_or_apikey")


def test_openai_adapter_timeout_then_fallback(monkeypatch):
    class FakeResp:
        status_code = 500

        def json(self):
            return {}

    def fake_post(*a, **kw):
        raise RuntimeError("boom")

    class FakeClient:
        def __init__(self, timeout=None):
            ...

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *a, **kw):
            return FakeResp()

    # httpx 없을 때도 폴백
    monkeypatch.setattr(oa, "httpx", types.SimpleNamespace(Client=FakeClient))
    adapter = oa.OpenAIAdapter()
    adapter.api_key = "dummy"
    adapter.retry = 0
    out = adapter.generate("hello")
    assert out["fallback_used"] is True
