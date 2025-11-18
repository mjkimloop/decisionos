import types
import apps.executor.plugins as plugs
import os
import pytest


def test_http_hmac_header_injected(monkeypatch):
    """Test that HMAC signature headers are added when key is configured"""
    os.environ["DECISIONOS_EXEC_HTTP_HMAC_KEY"] = "test-secret-key"
    os.environ["DECISIONOS_EXEC_HTTP_KEY_ID"] = "test-key-id"

    captured_headers = {}

    class FakeResp:
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {"ok": 1}

        @property
        def text(self):
            return '{"ok":1}'

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def request(self, method, url, headers=None, json=None):
            # Capture headers for verification
            captured_headers.update(headers or {})
            return FakeResp()

    fake_mod = types.SimpleNamespace()
    fake_mod.Client = FakeClient
    monkeypatch.setattr(plugs, "httpx", fake_mod, raising=True)

    out = plugs.http_call({"method": "POST", "url": "http://fake/api", "json": {"data": "test"}})
    assert out["status_code"] == 200

    # Verify HMAC headers were added
    assert "X-DecisionOS-Timestamp" in captured_headers
    assert "X-DecisionOS-Signature" in captured_headers
    assert "X-Key-Id" in captured_headers
    assert captured_headers["X-Key-Id"] == "test-key-id"

    # Cleanup
    os.environ.pop("DECISIONOS_EXEC_HTTP_HMAC_KEY", None)
    os.environ.pop("DECISIONOS_EXEC_HTTP_KEY_ID", None)
