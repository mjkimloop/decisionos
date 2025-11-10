# Invoice Template — 청구서 템플릿 (PDF/JSON)

**Version**: 1.0.0
**Last Updated**: 2025-11-03
**Owner**: Finance Operations Team
**Status**: Active

---

## 1. Overview

### 1.1 Invoice vs Receipt

| Document | Purpose | When Issued | Payment Status |
|----------|---------|-------------|----------------|
| **Invoice (청구서)** | Request for payment | Beginning of billing cycle | **NOT PAID** (payment due) |
| **Receipt (영수증)** | Proof of payment | After payment received | **PAID** |

**This document**: Invoice template (청구서)
**For receipts**: See [receipt_pdf.md](receipt_pdf.md)

---

## 2. Invoice Structure

### 2.1 Header
```
[DecisionOS Logo]

INVOICE / 청구서
Invoice No: INV-2025-11-00123
Issue Date: 2025-12-01
Due Date: 2025-12-04 (3 days)
Billing Period: 2025-11-01 ~ 2025-11-30
```

### 2.2 Bill To
```
Organization: TestCorp
Business Number: 123-45-67890
Contact: billing@testcorp.com
```

### 2.3 Line Items
```
Description                         Qty      Unit Price    Amount
──────────────────────────────────────────────────────────────
Pro Plan (Base Fee)                 1        ₩100,000     ₩100,000
Decision Calls (overage)         2,000       ₩2           ₩4,000
Storage (overage, 50 GB)            50       ₩80          ₩4,000
HITL Cases (overage, 100)          100       ₩500         ₩50,000
──────────────────────────────────────────────────────────────
Subtotal:                                                ₩158,000
VAT (10%):                                               ₩15,800
──────────────────────────────────────────────────────────────
TOTAL DUE:                                               ₩173,800
```

### 2.4 Payment Info
```
Payment Method: Credit Card on file (Visa **** 1234)
Auto-charge on: 2025-12-03
Or pay online: https://portal.decisionos.com/billing/invoices/INV-2025-11-00123
```

### 2.5 Footer
```
DecisionOS Inc.
Business Number: 987-65-43210
billing@decisionos.com | 1588-XXXX

Tax Invoice (세금계산서) will be issued separately within 10 days.
```

---

## 3. JSON Schema

```json
{
  "invoice_id": "INV-2025-11-00123",
  "status": "issued",  // "draft" | "issued" | "paid" | "overdue" | "void"
  "issued_at": "2025-12-01T00:00:00Z",
  "due_date": "2025-12-04T23:59:59Z",
  "billing_period": {
    "start": "2025-11-01",
    "end": "2025-11-30"
  },
  "org": {
    "org_id": "org_abc123",
    "name": "TestCorp",
    "business_number": "123-45-67890",
    "email": "billing@testcorp.com"
  },
  "plan": "pro",
  "line_items": [
    {
      "description": "Pro Plan (Base Fee)",
      "metric": "plan_base",
      "quantity": 1,
      "unit_price": 100000,
      "amount": 100000,
      "currency": "KRW"
    },
    {
      "description": "Decision Calls (overage)",
      "metric": "decision_calls",
      "quantity": 2000,
      "unit_price": 2,
      "amount": 4000,
      "currency": "KRW",
      "details": {
        "included": 5000,
        "used": 7000,
        "overage": 2000
      }
    }
  ],
  "summary": {
    "subtotal": 158000,
    "tax": 15800,
    "total": 173800,
    "currency": "KRW"
  },
  "payment": {
    "method": "card",
    "card_last4": "1234",
    "auto_charge_date": "2025-12-03"
  },
  "pdf_url": "https://cdn.decisionos.com/invoices/INV-2025-11-00123.pdf",
  "portal_url": "https://portal.decisionos.com/billing/invoices/INV-2025-11-00123"
}
```

---

## 4. Status Lifecycle

```
draft → issued → paid
          ↓
       overdue (if not paid by due date)
          ↓
       suspended (if 7+ days overdue)
```

---

## 5. Related Documents

- [Receipt Template](receipt_pdf.md) — Payment receipt (issued after invoice paid)
- [Billing Terms (Korean)](../docs/billing_terms_ko.md) — Customer-facing billing policy
- [Plans & Entitlements](../docs/plans_and_entitlements.md) — Pricing details

---

**END OF DOCUMENT**
