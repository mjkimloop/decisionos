import types
import apps.executor.plugins as plugs

def test_http_call_monkeypatched_client(monkeypatch):
    # httpx가 없어도 테스트 가능하게 httpx 대체 객체 삽입
    fake_mod = types.SimpleNamespace()
    class FakeResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        def json(self): return {"ok": True}
        text = ""
    class FakeClient:
        def __init__(self, timeout): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def request(self, method, url, headers=None, json=None): return FakeResp()

    fake_mod.Client = FakeClient
    monkeypatch.setattr(plugs, "httpx", fake_mod, raising=True)

    out = plugs.http_call({"action":"http.call","method":"GET","url":"http://fake"})
    assert out["status_code"] == 200 and out["json"] == {"ok": True}
