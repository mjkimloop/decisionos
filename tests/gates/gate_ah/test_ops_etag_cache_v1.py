import json
import importlib
from starlette.testclient import TestClient
import pytest

pytestmark = [pytest.mark.gate_ah]

def test_ops_etag_304(tmp_path, monkeypatch):
    # 인덱스/증빙 데이터 준비
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"files": [], "last_updated": "2025-01-01T00:00:00Z"}), encoding="utf-8")

    # 환경 경로 주입
    monkeypatch.setenv("DECISIONOS_EVIDENCE_ROOT", str(tmp_path))
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "*")

    from apps.ops.api import server
    importlib.reload(server)

    client = TestClient(server.app)

    # 1차 요청: 200 + ETag
    r1 = client.get("/ops/reason-trend?days=7")
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag, "ETag 헤더가 있어야 함"

    # 2차 요청: If-None-Match로 304
    r2 = client.get("/ops/reason-trend?days=7", headers={"If-None-Match": etag})
    assert r2.status_code == 304
