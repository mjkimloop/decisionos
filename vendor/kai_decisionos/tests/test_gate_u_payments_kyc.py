from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.billing.invoicer import close_month
from apps.ledger.postings import POSTINGS, clear_postings


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_payments_charge_refund_and_receipt():
    clear_postings()
    charge_resp = client.post(
        "/api/v1/pay/charge",
        headers={**HEADERS, "Idempotency-Key": "charge-001"},
        json={
            "org_id": "org-demo",
            "amount": 100000,
            "currency": "KRW",
            "pm_id": "tok_test",
            "adapter": "stripe_stub",
        },
    )
    assert charge_resp.status_code == 200, charge_resp.text
    body = charge_resp.json()
    assert body["status"] == "captured"
    charge = body["charge"]
    assert charge["amount"] == 100000
    receipt = body.get("receipt")
    assert receipt and receipt["tax_amount"] == 10000

    # idempotent retry returns same charge id
    retry = client.post(
        "/api/v1/pay/charge",
        headers={**HEADERS, "Idempotency-Key": "charge-001"},
        json={
            "org_id": "org-demo",
            "amount": 100000,
            "currency": "KRW",
            "pm_id": "tok_test",
            "adapter": "stripe_stub",
        },
    )
    assert retry.status_code == 200
    assert retry.json()["charge"]["id"] == charge["id"]

    refund_resp = client.post(
        "/api/v1/pay/refund",
        headers={**HEADERS, "Idempotency-Key": "refund-001"},
        json={"charge_id": charge["id"], "amount": 50000, "reason": "partial_refund"},
    )
    assert refund_resp.status_code == 200, refund_resp.text
    refund = refund_resp.json()
    assert refund["status"] == "refunded"
    assert refund["refund"]["amount"] == 50000
    accounts = {p.account for p in POSTINGS}
    assert "Cash" in accounts
    assert "Revenue" in accounts or "TaxPayable" in accounts

    reconcile_resp = client.post(
        "/api/v1/reconcile/match",
        headers=HEADERS,
        json={"charge_id": charge["id"], "amount": 100000, "currency": "KRW"},
    )
    assert reconcile_resp.status_code == 200
    assert reconcile_resp.json()["matched"] is True

    status_resp = client.get("/api/v1/reconcile/status", headers=HEADERS)
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["matched"] >= 1


def test_kyc_submission_and_status():
    submit = client.post(
        "/api/v1/kyc/submit",
        headers=HEADERS,
        json={
            "org_id": "org-demo",
            "type": "business",
            "docs": [{"doc_type": "business_license", "uri": "s3://bucket/license.pdf"}],
        },
    )
    assert submit.status_code == 201

    status = client.get("/api/v1/kyc/status", headers=HEADERS, params={"org_id": "org-demo"})
    assert status.status_code == 200
    body = status.json()
    assert body["status"] in {"verified", "needs_more", "rejected", "pending"}


def test_tax_calc_receipt_issue_and_dunning():
    invoice = close_month("org-demo", "2025-11", [{"description": "Subscription", "amount": 120000}])

    tax_resp = client.post(
        "/api/v1/tax/calc",
        headers=HEADERS,
        json={"invoice_id": invoice["id"], "country": "KR"},
    )
    assert tax_resp.status_code == 200
    assert tax_resp.json()["tax_total"] == 12000

    receipt_resp = client.post(
        "/api/v1/receipt/issue",
        headers=HEADERS,
        json={"invoice_id": invoice["id"]},
    )
    assert receipt_resp.status_code == 200
    receipt_body = receipt_resp.json()
    assert "receipt_id" in receipt_body
    assert receipt_body["pdf_url"].endswith(".pdf")

    dunning_resp = client.post(
        "/api/v1/pay/dunning/run",
        headers={**HEADERS, "Idempotency-Key": "dunning-001"},
        json={
            "org_id": "org-demo",
            "invoice_id": invoice["id"],
            "schedule": [{"channel": "email", "eta": "24h"}],
        },
    )
    assert dunning_resp.status_code == 200
    dunning_body = dunning_resp.json()
    assert dunning_body["status"] == "overdue"
    assert dunning_body["followups"], "schedule followup expected"
