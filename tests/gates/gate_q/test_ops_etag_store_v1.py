import os
from starlette.testclient import TestClient

os.environ.setdefault("DECISIONOS_ALLOW_SCOPES", "ops:read")

from apps.ops.api.server import app  # noqa: E402


def test_etag_304_flow():
    client = TestClient(app)
    r1 = client.get("/ops/reason-trend")
    assert r1.status_code == 200
    etag = r1.headers.get("etag")
    assert etag

    r2 = client.get("/ops/reason-trend", headers={"If-None-Match": etag})
    assert r2.status_code == 304
