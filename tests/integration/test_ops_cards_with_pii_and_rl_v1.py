import os
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.ops.ratelimit import build_limiter
from apps.security.pii import redact_text

pytestmark = pytest.mark.integration

app = FastAPI()
rate_limiter = build_limiter()


def rbac_dep():
    scopes = os.getenv("DECISIONOS_ALLOW_SCOPES", "")
    if "ops:read" not in scopes and "*" not in scopes:
        raise HTTPException(status_code=403, detail="forbidden")
    return True


@app.get("/ops/cards/reason-trends")
def reasons(summary: str = "연락처 test@example.com", _: bool = Depends(rbac_dep)):
    allowed, _ = rate_limiter.allow("ops:read")
    if not allowed:
        raise HTTPException(status_code=429, detail="rate-limited")
    return {"data": [{"text": redact_text(summary)}]}


def test_pii_and_rate_limit(monkeypatch):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")
    client = TestClient(app)
    response = client.get("/ops/cards/reason-trends")
    assert response.status_code in (200, 429)
    if response.status_code == 200:
        assert "@" not in response.json()["data"][0]["text"]
