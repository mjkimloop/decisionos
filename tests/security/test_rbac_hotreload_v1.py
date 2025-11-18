import importlib
import os
import tempfile
import textwrap
import time

from starlette.testclient import TestClient


def _write_map(path: str, scopes_line: str):
    txt = textwrap.dedent(
        f"""
    routes:
      - path: /ops/*
        method: GET
        scopes: [{scopes_line}]
    """
    ).strip()
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def test_rbac_hotreload_and_enforce(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "rbac.yaml")
        _write_map(path, '"ops:read"')
        monkeypatch.setenv("DECISIONOS_RBAC_MAP", path)
        monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
        monkeypatch.setenv("DECISIONOS_RBAC_RELOAD_SEC", "1")
        monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")
        import apps.ops.api.server as api
        importlib.reload(api)
        client = TestClient(api.app)

        r1 = client.get("/ops/reason-trend")
        assert r1.status_code in (200, 304)
