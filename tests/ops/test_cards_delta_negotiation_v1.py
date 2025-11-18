from starlette.testclient import TestClient

from apps.ops.api.server import app


def test_delta_negotiation_cases(monkeypatch, tmp_path):
    # 빈 인덱스라도 동작하도록 기본 경로 주입
    idx = tmp_path / "index.json"
    idx.write_text('{"buckets":[],"generated_at":"2025-11-18T00:00:00Z"}', encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    client = TestClient(app)
    headers = {"X-Scopes": "ops:read"}

    r1 = client.get("/ops/cards/reason-trends", headers=headers)
    etag = r1.headers["ETag"]
    assert r1.status_code == 200 and "X-Delta-Accepted" in r1.headers

    r2 = client.get("/ops/cards/reason-trends", headers={**headers, "X-Delta-Base-ETag": etag})
    assert r2.headers.get("X-Delta-Accepted") == "1"

    r3 = client.get("/ops/cards/reason-trends", headers={**headers, "X-Delta-Base-ETag": "W/invalid"})
    assert r3.headers.get("X-Delta-Accepted") == "0"
