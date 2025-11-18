from starlette.testclient import TestClient

from apps.judge.server import app as judge_app


def test_readyz_shape_keys():
    c = TestClient(judge_app)
    r = c.get("/readyz")
    assert r.status_code in (200, 503)
    j = r.json()
    assert "checks" in j
    m = c.get("/metrics")
    assert m.status_code == 200
