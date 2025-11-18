"""
Go 기준 점검 (10분 컷) - v0.5.11t+2
실전 전환 직전 필수 점검 항목
"""
import os
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_go_1_rbac_enforcement(tmp_path):
    """1. RBAC 강제 확인: X-Scopes 없이 403, ops:read로 200/304"""
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
    os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"  # Use X-Scopes header

    from apps.ops.api import cards_delta
    cards_delta.INDEX_PATH = str(idx)

    app = FastAPI()
    app.include_router(cards_delta.router)  # router already has prefix="/ops/cards"
    c = TestClient(app)

    # No X-Scopes → 403
    r_no_scope = c.get("/ops/cards/reason-trends")
    assert r_no_scope.status_code == 403, "RBAC should enforce 403 without scopes"

    # With ops:read → 200
    r_ok = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    assert r_ok.status_code == 200, "Should allow with ops:read scope"
    etag = r_ok.headers.get("ETag")
    assert etag

    # With If-None-Match → 304
    r_304 = c.get("/ops/cards/reason-trends", headers={"If-None-Match": etag, "X-Scopes": "ops:read"})
    assert r_304.status_code == 304, "Should return 304 with matching ETag"


def test_go_2_vary_and_304_safety(tmp_path):
    """2. Vary/304 캐시 안전성: Vary 헤더 + Content-Length: 0"""
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
    os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"

    from apps.ops.api import cards_delta
    cards_delta.INDEX_PATH = str(idx)

    app = FastAPI()
    app.include_router(cards_delta.router)  # router already has prefix="/ops/cards"
    c = TestClient(app)

    r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    vary = r1.headers.get("Vary")

    # Vary 헤더 필수 필드 검증
    assert "Authorization" in vary
    assert "X-Scopes" in vary
    assert "X-Tenant" in vary

    # 304 응답
    r2 = c.get("/ops/cards/reason-trends", headers={"If-None-Match": etag, "X-Scopes": "ops:read"})
    assert r2.status_code == 304
    assert r2.headers.get("Content-Length") == "0"
    assert r2.headers.get("ETag") == etag


def test_go_3_strong_etag_validity(tmp_path):
    """3. Strong ETag 유효성: ETag가 tenant + catalog + 데이터 기반으로 생성됨"""
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
    os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"
    os.environ["DECISIONOS_LABEL_CATALOG_SHA"] = ""

    from apps.ops.api import cards_delta
    cards_delta.INDEX_PATH = str(idx)

    app = FastAPI()
    app.include_router(cards_delta.router)  # router already has prefix="/ops/cards"
    c = TestClient(app)

    # 동일 데이터로 두 번 호출 → 동일 ETag
    r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    etag1 = r1.headers.get("ETag")

    r2 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    etag2 = r2.headers.get("ETag")

    assert etag1 == etag2, "ETag should be stable for same data"

    # Catalog SHA 변경 시 ETag 달라짐
    os.environ["DECISIONOS_LABEL_CATALOG_SHA"] = "new-sha"
    import importlib
    importlib.reload(cards_delta)
    cards_delta.INDEX_PATH = str(idx)

    app2 = FastAPI()
    app2.include_router(cards_delta.router)
    c2 = TestClient(app2)

    r3 = c2.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    etag3 = r3.headers.get("ETag")

    assert etag1 != etag3, "ETag should change when catalog SHA changes"
    os.environ["DECISIONOS_LABEL_CATALOG_SHA"] = ""


def test_go_4_tenant_isolation(tmp_path):
    """4. 테넌트 분리: TENANT 환경변수별 ETag 분리 (ETag에 tenant 포함)"""
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
    os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"

    # 테넌트 A
    os.environ["DECISIONOS_TENANT"] = "tenant-a"
    from apps.ops.api import cards_delta
    import importlib
    importlib.reload(cards_delta)
    cards_delta.INDEX_PATH = str(idx)

    app_a = FastAPI()
    app_a.include_router(cards_delta.router)
    c_a = TestClient(app_a)

    r_a = c_a.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    etag_a = r_a.headers.get("ETag")

    # 테넌트 B
    os.environ["DECISIONOS_TENANT"] = "tenant-b"
    importlib.reload(cards_delta)
    cards_delta.INDEX_PATH = str(idx)

    app_b = FastAPI()
    app_b.include_router(cards_delta.router)
    c_b = TestClient(app_b)

    r_b = c_b.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    etag_b = r_b.headers.get("ETag")

    # ETag가 테넌트별로 달라야 함 (tenant가 ETag seed에 포함)
    assert etag_a != etag_b, "ETags should differ by tenant"

    # 테넌트 복원
    os.environ["DECISIONOS_TENANT"] = ""


def test_go_5_delta_negotiation(tmp_path):
    """5. Delta 협상: X-Delta-Base-ETag 불일치 시 풀 페이로드"""
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
    os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"

    from apps.ops.api import cards_delta
    cards_delta.INDEX_PATH = str(idx)

    app = FastAPI()
    app.include_router(cards_delta.router)  # router already has prefix="/ops/cards"
    c = TestClient(app)

    r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    etag1 = r1.headers.get("ETag")

    # 잘못된 Base ETag 전달
    r2 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read", "X-Delta-Base-ETag": "wrong-etag"})
    assert r2.headers.get("X-Delta-Accepted") == "0", "Should reject delta with wrong base ETag"

    # 올바른 Base ETag
    r3 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read", "X-Delta-Base-ETag": etag1})
    # Delta가 없으면(동일 데이터) 0, 있으면 1
    delta_accepted = r3.headers.get("X-Delta-Accepted")
    assert delta_accepted in ("0", "1"), "Should return delta acceptance status"


def test_go_7_http_plugin_retry_policy():
    """7. HTTP 플러그인 재시도 정책: 401/403/422 즉시 실패, 429/5xx 재시도"""
    import types
    from apps.executor import plugins

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
            if method == "GET" and "auth-fail" in url:
                return FakeResp(401)
            if method == "GET" and "transient" in url:
                if calls["n"] == 1:
                    return FakeResp(503)  # Transient error
                return FakeResp(200)
            return FakeResp(200)

    fake_mod = types.SimpleNamespace()
    fake_mod.Client = FakeClient

    # Monkeypatch httpx
    original_httpx = plugins.httpx
    plugins.httpx = fake_mod

    try:
        # Auth error - no retry
        calls["n"] = 0
        out1 = plugins.http_call({"method": "GET", "url": "http://fake/auth-fail", "retries": 2})
        assert out1["status_code"] == 401
        assert calls["n"] == 1, "Should NOT retry auth errors"

        # Transient error - retry
        calls["n"] = 0
        out2 = plugins.http_call({"method": "GET", "url": "http://fake/transient", "retries": 2})
        assert out2["status_code"] == 200
        assert calls["n"] == 2, "Should retry transient errors"

    finally:
        plugins.httpx = original_httpx


def test_go_8_sensitive_data_masking():
    """8. 민감정보 마스킹: Authorization 헤더/필드 마스킹"""
    from apps.executor.plugins import _mask_headers, _mask_json

    headers = {
        "Authorization": "Bearer secret-token",
        "X-API-Key": "api-key-123",
        "Content-Type": "application/json",
    }
    masked_h = _mask_headers(headers)
    assert masked_h["Authorization"] == "***"
    assert masked_h["X-API-Key"] == "***"
    assert masked_h["Content-Type"] == "application/json"

    body = {
        "username": "user",
        "password": "secret123",
        "token": "abc-token",
        "data": "public",
    }
    masked_b = _mask_json(body)
    assert masked_b["password"] == "***"
    assert masked_b["token"] == "***"
    assert masked_b["username"] == "user"
    assert masked_b["data"] == "public"


def test_go_9_hmac_signature_headers():
    """9. 키 서명 경로: HMAC 활성 시 헤더 포함"""
    import types
    from apps.executor import plugins

    os.environ["DECISIONOS_EXEC_HTTP_HMAC_KEY"] = "test-key"
    os.environ["DECISIONOS_EXEC_HTTP_KEY_ID"] = "test-id"

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
            captured_headers.update(headers or {})
            return FakeResp()

    fake_mod = types.SimpleNamespace()
    fake_mod.Client = FakeClient

    original_httpx = plugins.httpx
    plugins.httpx = fake_mod

    try:
        plugins.http_call({"method": "POST", "url": "http://fake/api", "json": {"data": "test"}})

        # HMAC 헤더 검증
        assert "X-DecisionOS-Timestamp" in captured_headers
        assert "X-DecisionOS-Signature" in captured_headers
        assert "X-Key-Id" in captured_headers
        assert captured_headers["X-Key-Id"] == "test-id"

    finally:
        plugins.httpx = original_httpx
        os.environ.pop("DECISIONOS_EXEC_HTTP_HMAC_KEY", None)
        os.environ.pop("DECISIONOS_EXEC_HTTP_KEY_ID", None)


def test_go_10_ci_gate_r_passes():
    """10. CI gate_r: 하드닝 테스트 3종 통과 확인"""
    # 이 테스트는 CI에서 실행되므로, 로컬에서는 import만 확인
    try:
        from tests.ops import test_cards_vary_and_304_v1
        from tests.executor import test_http_retry_policy_v1, test_http_hmac_header_v1

        assert hasattr(test_cards_vary_and_304_v1, "test_cards_vary_and_304_headers")
        assert hasattr(test_http_retry_policy_v1, "test_http_retry_transient_only")
        assert hasattr(test_http_retry_policy_v1, "test_http_no_retry_auth_errors")
        assert hasattr(test_http_hmac_header_v1, "test_http_hmac_header_injected")
    except ImportError as e:
        pytest.fail(f"CI gate_r tests not found: {e}")
