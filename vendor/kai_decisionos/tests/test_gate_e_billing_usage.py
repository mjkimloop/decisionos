from __future__ import annotations

import json
import hmac, hashlib

from fastapi.testclient import TestClient

from apps.gateway.main import app
from packages.common.config import settings

client = TestClient(app)
HEADERS = {"X-Api-Key":"dev-key","X-Role":"admin","X-Tenant-ID":"demo-tenant"}


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_usage_event_hmac_and_summary(monkeypatch):
    monkeypatch.setattr(settings, 'usage_hmac_secret', 'secret')
    body = json.dumps({"org_id":"orgA","event":"decide.ok","value":1}).encode('utf-8')
    sig = _sign('secret', body)
    r = client.post('/api/v1/usage/events', data=body, headers={**HEADERS, "X-Signature": sig, "Idempotency-Key":"e1"})
    assert r.status_code == 200
    # duplicate idempotency
    r2 = client.post('/api/v1/usage/events', data=body, headers={**HEADERS, "X-Signature": sig, "Idempotency-Key":"e1"})
    assert r2.status_code == 200 and r2.json().get('status') == 'duplicate'
    # summary
    s = client.get('/api/v1/usage/summary', params={"org_id":"orgA"}, headers=HEADERS)
    assert s.status_code == 200
    assert s.json().get('metrics',{}).get('decide.ok',0) >= 1


def test_billing_preview_finalize_and_pdf(monkeypatch):
    # ensure monthly usage for period
    from apps.meter.collector import MONTHLY
    MONTHLY.clear()
    MONTHLY[("orgA","decision_calls","2025-11")] = 10
    # preview via existing endpoint (close is finalize)
    pr = client.post('/api/v1/billing/invoices/close', headers=HEADERS, json={"org_id":"orgA","yyyymm":"2025-11","unit_price":0.002,"metric":"decision_calls"})
    assert pr.status_code == 200
    inv_id = pr.json().get('id')
    # pdf
    g = client.get(f'/api/v1/billing/invoices/{inv_id}', params={"fmt":"pdf"}, headers=HEADERS)
    assert g.status_code == 200 and 'pdf_b64' in g.json()

