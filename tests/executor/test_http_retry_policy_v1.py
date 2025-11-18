import types
import apps.executor.plugins as plugs
import pytest


def test_http_retry_transient_only(monkeypatch):
    """Test that HTTP plugin retries transient errors but not auth errors"""
    calls = {"n": 0}

    class FakeResp:
        def __init__(self, sc):
            self.status_code = sc
            self.headers = {"content-type": "application/json"}
            self._text = '{"ok":1}'

        def json(self):
            return {"ok": 1}

        @property
        def text(self):
            return self._text

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def request(self, method, url, headers=None, json=None):
            calls["n"] += 1
            if calls["n"] == 1:
                # First call: network error
                raise Exception("Connection error")
            # Second call: success
            return FakeResp(200)

    fake_mod = types.SimpleNamespace()
    fake_mod.Client = FakeClient
    monkeypatch.setattr(plugs, "httpx", fake_mod, raising=True)

    out = plugs.http_call({"method": "GET", "url": "http://fake", "retries": 2, "timeout_sec": 1})
    assert out["status_code"] == 200
    assert calls["n"] == 2  # First failed, second succeeded


def test_http_no_retry_auth_errors(monkeypatch):
    """Test that 401/403/422 are not retried"""
    calls = {"n": 0}

    class FakeResp:
        def __init__(self, sc):
            self.status_code = sc
            self.headers = {"content-type": "application/json"}
            self._text = '{"error":"unauthorized"}'

        def json(self):
            return {"error": "unauthorized"}

        @property
        def text(self):
            return self._text

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def request(self, method, url, headers=None, json=None):
            calls["n"] += 1
            return FakeResp(401)

    fake_mod = types.SimpleNamespace()
    fake_mod.Client = FakeClient
    monkeypatch.setattr(plugs, "httpx", fake_mod, raising=True)

    out = plugs.http_call({"method": "GET", "url": "http://fake", "retries": 2, "timeout_sec": 1})
    assert out["status_code"] == 401
    assert calls["n"] == 1  # Should not retry auth errors
