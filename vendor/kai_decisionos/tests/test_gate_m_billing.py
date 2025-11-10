from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.billing import ratebook
from apps.meter import collector


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_selfserve_ratebook_payments_and_reconcile(tmp_path, monkeypatch):
    ratebook_file = tmp_path / "ratebook.json"
    ratebook_file.write_text(
        json.dumps(
            {
                "trial": {"decision_calls": 0.0},
                "growth": {"decision_calls": 0.003},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ratebook, "DEFAULT_RATEBOOK_PATH", ratebook_file)
    ratebook.clear_cache()

    collector.MONTHLY.clear()

    org_resp = client.post("/api/v1/orgs", headers=HEADERS, json={"name": "Acme", "plan": "trial"})
    assert org_resp.status_code == 200
    org_id = org_resp.json()["id"]

    rb = client.get("/api/v1/billing/selfserve/ratebook", headers=HEADERS)
    assert rb.status_code == 200 and "growth" in rb.json()

    sub = client.post(
        "/api/v1/billing/selfserve/subscribe",
        headers=HEADERS,
        json={"org_id": org_id, "plan": "growth"},
    )
    assert sub.status_code == 200 and sub.json()["plan"] == "growth"

    ent = client.post(
        "/api/v1/entitlements/check",
        headers=HEADERS,
        json={"org_id": org_id, "feature": "guardrails.v2"},
    )
    assert ent.json()["ok"] is True

    period = "2025-11"
    collector.MONTHLY[(org_id, "decision_calls", period)] = 1500.0
    invoice = client.post(
        "/api/v1/billing/invoices/close",
        headers=HEADERS,
        json={"org_id": org_id, "yyyymm": period, "unit_price": 0.003, "metric": "decision_calls"},
    )
    assert invoice.status_code == 200
    invoice_data = invoice.json()
    invoice_id = invoice_data["id"]
    assert invoice_data["balance_due"] == invoice_data["total"]

    partial = client.post(
        "/api/v1/payments/record",
        headers=HEADERS,
        json={"invoice_id": invoice_id, "amount": invoice_data["total"] / 2, "method": "card"},
    )
    assert partial.status_code == 200

    invoice_after = client.get(f"/api/v1/billing/invoices/{invoice_id}", headers=HEADERS)
    assert invoice_after.status_code == 200
    remaining = invoice_after.json()["balance_due"]
    assert 0 < remaining < invoice_after.json()["total"]

    dunning = client.post(
        "/api/v1/payments/dunning",
        headers=HEADERS,
        json={"invoice_id": invoice_id, "reason": "partial", "channel": "email", "eta": "2025-11-10T09:00:00Z"},
    )
    assert dunning.status_code == 200
    status = client.get(f"/api/v1/payments/dunning/{invoice_id}", headers=HEADERS)
    assert status.status_code == 200 and status.json()["status"] == "overdue"

    final_pay = client.post(
        "/api/v1/payments/record",
        headers=HEADERS,
        json={"invoice_id": invoice_id, "amount": remaining, "method": "card"},
    )
    assert final_pay.status_code == 200
    payment_id = final_pay.json()["payment_id"]

    rec = client.post(
        "/api/v1/payments/reconcile",
        headers=HEADERS,
        json={"invoice_id": invoice_id, "payment_id": payment_id, "amount": remaining},
    )
    assert rec.status_code == 200

    reconcile_status = client.get(f"/api/v1/payments/reconcile/{invoice_id}", headers=HEADERS)
    assert reconcile_status.status_code == 200
    assert reconcile_status.json()["payment_id"] == payment_id
