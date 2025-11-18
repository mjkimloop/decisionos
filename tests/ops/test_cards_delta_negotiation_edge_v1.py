"""
Delta 협상 엣지 케이스 테스트

3가지 케이스:
1. X-Delta-Base-ETag 헤더 없음 → delta=null
2. X-Delta-Base-ETag 불일치 → X-Delta-Accepted: 0
3. X-Delta-Base-ETag 일치 + 변경사항 있음 → X-Delta-Accepted: 1
"""
import json
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_delta_no_header():
    """케이스 1: X-Delta-Base-ETag 헤더 없음 → delta=null"""
    with tempfile.TemporaryDirectory() as tmpdir:
        idx = Path(tmpdir) / "index.json"
        idx.write_text('{"generated_at":1234567890,"buckets":[{"reasons":{"perf":3}}]}', encoding="utf-8")
        os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
        os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"

        from apps.ops.api import cards_delta
        import importlib
        importlib.reload(cards_delta)

        app = FastAPI()
        app.include_router(cards_delta.router)
        c = TestClient(app)

        r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
        assert r1.status_code == 200
        body1 = r1.json()

        assert body1.get("delta") is None, "Delta should be None when no header"
        assert r1.headers.get("X-Delta-Accepted") == "0"


def test_delta_wrong_base_etag():
    """케이스 2: X-Delta-Base-ETag 불일치 → X-Delta-Accepted: 0"""
    with tempfile.TemporaryDirectory() as tmpdir:
        idx = Path(tmpdir) / "index.json"
        idx.write_text('{"generated_at":1234567890,"buckets":[{"reasons":{"perf":3}}]}', encoding="utf-8")
        os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
        os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"

        from apps.ops.api import cards_delta
        import importlib
        importlib.reload(cards_delta)

        app = FastAPI()
        app.include_router(cards_delta.router)
        c = TestClient(app)

        r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
        correct_etag = r1.headers.get("ETag")

        wrong_etag = '"wrong-etag-12345"'
        r2 = c.get(
            "/ops/cards/reason-trends",
            headers={"X-Scopes": "ops:read", "X-Delta-Base-ETag": wrong_etag}
        )
        assert r2.headers.get("X-Delta-Accepted") == "0"
        assert r2.json().get("delta") is None


def test_delta_force_full_probe():
    """강제 풀 페이로드 프로브 (FORCE_FULL_PROBE_PCT=100)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        idx = Path(tmpdir) / "index.json"
        data = {"generated_at":1234567890,"buckets":[{"reasons":{"perf":10}}]}
        idx.write_text(json.dumps(data), encoding="utf-8")

        os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
        os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"
        os.environ["DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT"] = "100"

        from apps.ops.api import cards_delta
        import importlib
        importlib.reload(cards_delta)

        app = FastAPI()
        app.include_router(cards_delta.router)
        c = TestClient(app)

        r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
        etag1 = r1.headers.get("ETag")

        r2 = c.get(
            "/ops/cards/reason-trends",
            headers={"X-Scopes": "ops:read", "X-Delta-Base-ETag": etag1}
        )
        assert r2.headers.get("X-Delta-Accepted") == "0"
        assert r2.headers.get("X-Delta-Probe") == "1"

        os.environ.pop("DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT", None)
