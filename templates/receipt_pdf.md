# 영수증 템플릿 — Receipt PDF/JSON Template

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Owner**: Finance Operations Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This document defines the **structure and layout** for payment receipts issued by DecisionOS. Receipts are generated in:
- **PDF format**: For customer download and print
- **JSON format**: For API access and programmatic integration

**Use Cases**:
- Customer requests receipt for expense reimbursement
- Accounting integration (export to ERP systems)
- Tax filing (VAT reporting)
- Audit trail (compliance with financial regulations)

---

### 1.2 Receipt Types

| Type | Description | When Issued | Includes VAT? |
|------|-------------|-------------|---------------|
| **Payment Receipt** (결제 영수증) | Issued when payment is captured | After successful payment | Yes (개인/사업자) |
| **Refund Receipt** (환불 영수증) | Issued when refund is processed | After refund completed | Yes (negative amount) |
| **Tax Invoice** (세금계산서) | Official tax document for business customers | Within 10 days of next month | Yes (separate document) |

**Note**: This template covers **Payment Receipt** and **Refund Receipt**. Tax invoices follow a separate government-regulated format (국세청 전자세금계산서).

---

## 2. PDF Receipt Layout

### 2.1 Header Section

```
┌──────────────────────────────────────────────────────────────┐
│                          RECEIPT                             │
│                          영수증                               │
│                                                              │
│  Logo: [DecisionOS Logo]                  Receipt No: R-2025-11-00123  │
│                                           Issue Date: 2025-11-04        │
│                                           Payment Date: 2025-11-03      │
└──────────────────────────────────────────────────────────────┘
```

**Fields**:
- **Receipt No**: Unique identifier (format: `R-YYYY-MM-NNNNN`)
- **Issue Date**: Date receipt was generated (UTC, displayed in KST)
- **Payment Date**: Date payment was captured

---

### 2.2 Customer Information

```
┌──────────────────────────────────────────────────────────────┐
│  Bill To (청구 대상):                                          │
│  ────────────────────────────────────────────────────────    │
│  Customer Name:   {customer_name}                            │
│  Organization:    {organization_name}                        │
│  Business Number: {business_number} (사업자 등록번호, if applicable) │
│  Email:           {email}                                    │
│  Phone:           {phone}                                    │
└──────────────────────────────────────────────────────────────┘
```

**Data Source**:
- `customer_name`: From KYC record or account profile
- `organization_name`: Org display name
- `business_number`: From KYC verification (format: `XXX-XX-XXXXX`)

---

### 2.3 Payment Details

```
┌──────────────────────────────────────────────────────────────┐
│  Payment Details (결제 내역):                                  │
│  ────────────────────────────────────────────────────────    │
│  Invoice Number:       {invoice_id}                          │
│  Billing Period:       {billing_period_start} ~ {billing_period_end} │
│  Payment Method:       {payment_method}                      │
│  Card Last 4 Digits:   **** **** **** {last4} (if card)      │
│  Transaction ID:       {charge_id}                           │
└──────────────────────────────────────────────────────────────┘
```

**Fields**:
- **Invoice Number**: Links to the original invoice (e.g., `INV-2025-11-00456`)
- **Billing Period**: Service usage period (e.g., `2025-10-01 ~ 2025-10-31`)
- **Payment Method**: `Credit Card`, `Bank Transfer`, `Wire` (카드, 계좌이체, 무통장입금)
- **Card Last 4 Digits**: Security (only show last 4, never full card number)
- **Transaction ID**: PG charge ID (e.g., `ch_1A2B3C4D5E6F`)

---

### 2.4 Itemized Charges

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Itemized Charges (상세 내역):                                                │
│  ──────────────────────────────────────────────────────────────────────────  │
│  Description                          Qty    Unit Price    Amount    Tax Rate │
│  ──────────────────────────────────────────────────────────────────────────  │
│  DecisionOS Pro Plan - Nov 2025        1    ₩100,000     ₩100,000    10%     │
│  API Calls (overage)                5,000    ₩10          ₩50,000     10%     │
│  Storage (overage, 50GB)              50    ₩500         ₩25,000     10%     │
│  ──────────────────────────────────────────────────────────────────────────  │
│  Subtotal (소계):                                         ₩175,000            │
│  VAT (10%, 부가세):                                       ₩17,500             │
│  ──────────────────────────────────────────────────────────────────────────  │
│  Total Amount (합계):                                     ₩192,500            │
│  Amount Paid (결제 금액):                                 ₩192,500            │
│  ──────────────────────────────────────────────────────────────────────────  │
│  Balance Due (잔액):                                      ₩0                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Calculation**:
```
Subtotal = Σ(Qty × Unit Price)
VAT = Subtotal × 0.10 (10% for South Korea)
Total = Subtotal + VAT
Balance = Total - Amount Paid (should be ₩0 for receipts)
```

**Multi-Currency**:
- If payment in USD: Show both USD and KRW (exchange rate snapshot)
- Example: `$100.00 USD (₩130,000 KRW at rate 1,300.00)`

---

### 2.5 Footer Section

```
┌──────────────────────────────────────────────────────────────┐
│  Payment Status (결제 상태): PAID ✓                           │
│                                                              │
│  Notes (비고):                                                │
│  • This is an official receipt for payment received.        │
│  • For tax invoice (세금계산서), see separate document.       │
│  • Questions? Contact billing@decisionos.com                │
│                                                              │
│  ──────────────────────────────────────────────────────────  │
│  DecisionOS Inc.                                             │
│  Address: 123 Teheran-ro, Gangnam-gu, Seoul, South Korea    │
│  Business Number: 123-45-67890                              │
│  Email: billing@decisionos.com | Phone: +82-2-1234-5678     │
│                                                              │
│  Generated: 2025-11-04 14:23:45 KST                          │
│  Audit Link: https://audit.decisionos.com/receipts/R-2025-11-00123 │
└──────────────────────────────────────────────────────────────┘
```

**Audit Link**:
- Cryptographic hash of receipt (ensures tamper-proof)
- Publicly verifiable via blockchain or audit trail API

---

## 3. JSON Receipt Structure

### 3.1 Schema (OpenAPI 3.0)

```json
{
  "receipt_id": "R-2025-11-00123",
  "receipt_type": "payment",  // "payment" | "refund"
  "issued_at": "2025-11-04T05:23:45Z",  // UTC
  "payment_date": "2025-11-03T08:15:30Z",

  "customer": {
    "customer_id": "cust_a1b2c3d4",
    "name": "홍길동",
    "organization": "DecisionOS Test Org",
    "business_number": "123-45-67890",  // Optional
    "email": "hong@example.com",
    "phone": "+82-10-1234-5678"
  },

  "payment": {
    "invoice_id": "INV-2025-11-00456",
    "billing_period_start": "2025-10-01",
    "billing_period_end": "2025-10-31",
    "payment_method": "card",  // "card" | "bank_transfer" | "wire"
    "card_brand": "Visa",  // If card
    "card_last4": "1234",  // If card
    "transaction_id": "ch_1A2B3C4D5E6F",
    "pg_provider": "stripe"  // "stripe" | "inicis" | "kcp"
  },

  "line_items": [
    {
      "description": "DecisionOS Pro Plan - Nov 2025",
      "quantity": 1,
      "unit_price": 100000,
      "amount": 100000,
      "currency": "KRW",
      "tax_rate": 0.10,
      "tax_amount": 10000
    },
    {
      "description": "API Calls (overage)",
      "quantity": 5000,
      "unit_price": 10,
      "amount": 50000,
      "currency": "KRW",
      "tax_rate": 0.10,
      "tax_amount": 5000
    },
    {
      "description": "Storage (overage, 50GB)",
      "quantity": 50,
      "unit_price": 500,
      "amount": 25000,
      "currency": "KRW",
      "tax_rate": 0.10,
      "tax_amount": 2500
    }
  ],

  "summary": {
    "subtotal": 175000,
    "tax_total": 17500,
    "total": 192500,
    "amount_paid": 192500,
    "balance_due": 0,
    "currency": "KRW"
  },

  "status": "paid",  // "paid" | "refunded" | "partially_refunded"

  "notes": [
    "This is an official receipt for payment received.",
    "For tax invoice (세금계산서), see separate document.",
    "Questions? Contact billing@decisionos.com"
  ],

  "issuer": {
    "company_name": "DecisionOS Inc.",
    "business_number": "123-45-67890",
    "address": "123 Teheran-ro, Gangnam-gu, Seoul, South Korea",
    "email": "billing@decisionos.com",
    "phone": "+82-2-1234-5678"
  },

  "audit": {
    "generated_at": "2025-11-04T05:23:45Z",
    "audit_link": "https://audit.decisionos.com/receipts/R-2025-11-00123",
    "hash": "sha256:a1b2c3d4e5f6...",  // SHA-256 hash of receipt content
    "signature": "ecdsa:...",  // Optional digital signature
    "blockchain_tx": null  // Optional blockchain anchor (if implemented)
  },

  "pdf_uri": "https://cdn.decisionos.com/receipts/R-2025-11-00123.pdf",
  "json_uri": "https://api.decisionos.com/v1/receipts/R-2025-11-00123.json"
}
```

---

### 3.2 Refund Receipt Example

**Differences from Payment Receipt**:
- `receipt_type`: `"refund"`
- `line_items`: Negative amounts
- `summary.amount_paid`: Negative (refund amount)
- Additional fields: `refund_reason`, `original_receipt_id`

```json
{
  "receipt_id": "R-2025-11-00124",
  "receipt_type": "refund",
  "issued_at": "2025-11-05T02:10:15Z",
  "refund_date": "2025-11-05T02:05:30Z",

  "customer": { /* same as payment receipt */ },

  "payment": {
    "original_receipt_id": "R-2025-11-00123",
    "original_transaction_id": "ch_1A2B3C4D5E6F",
    "refund_transaction_id": "re_9Z8Y7X6W5V4U",
    "payment_method": "card",
    "card_brand": "Visa",
    "card_last4": "1234"
  },

  "line_items": [
    {
      "description": "Refund: API Calls (overage) - Partial",
      "quantity": -2500,  // Negative for refund
      "unit_price": 10,
      "amount": -25000,
      "currency": "KRW",
      "tax_rate": 0.10,
      "tax_amount": -2500
    }
  ],

  "summary": {
    "subtotal": -25000,
    "tax_total": -2500,
    "total": -27500,
    "amount_paid": -27500,  // Negative = refund
    "balance_due": 0,
    "currency": "KRW"
  },

  "status": "refunded",

  "refund_reason": "Customer requested partial refund due to service downtime",

  "notes": [
    "This is a refund receipt. Amount will be credited to original payment method.",
    "Refund processing time: 5-10 business days.",
    "Questions? Contact billing@decisionos.com"
  ],

  /* issuer, audit fields same as above */
}
```

---

## 4. PDF Generation

### 4.1 Template Engine

**Technology Stack**:
- **Library**: `wkhtmltopdf` (HTML → PDF) or `WeasyPrint` (Python-native)
- **Template**: Jinja2 (HTML template with variables)
- **Styling**: CSS (embedded in HTML for offline rendering)

**Example Jinja2 Template** (`receipt_template.html`):
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Receipt {{ receipt.receipt_id }}</title>
  <style>
    body { font-family: 'Noto Sans KR', Arial, sans-serif; margin: 40px; }
    .header { text-align: center; margin-bottom: 30px; }
    .header h1 { font-size: 24px; margin: 0; }
    .section { margin-bottom: 20px; border: 1px solid #ccc; padding: 15px; }
    .section h2 { font-size: 16px; border-bottom: 2px solid #000; padding-bottom: 5px; }
    table { width: 100%; border-collapse: collapse; }
    table th, table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    table th { background-color: #f2f2f2; font-weight: bold; }
    .total-row { font-weight: bold; background-color: #e6f2ff; }
    .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
  </style>
</head>
<body>
  <div class="header">
    <img src="logo.png" alt="DecisionOS" width="150">
    <h1>RECEIPT / 영수증</h1>
    <p>Receipt No: {{ receipt.receipt_id }} | Issue Date: {{ receipt.issued_at | format_datetime }}</p>
  </div>

  <div class="section">
    <h2>Bill To (청구 대상)</h2>
    <p><strong>Name:</strong> {{ receipt.customer.name }}</p>
    <p><strong>Organization:</strong> {{ receipt.customer.organization }}</p>
    {% if receipt.customer.business_number %}
    <p><strong>Business Number:</strong> {{ receipt.customer.business_number }}</p>
    {% endif %}
    <p><strong>Email:</strong> {{ receipt.customer.email }}</p>
  </div>

  <div class="section">
    <h2>Payment Details (결제 내역)</h2>
    <p><strong>Invoice:</strong> {{ receipt.payment.invoice_id }}</p>
    <p><strong>Billing Period:</strong> {{ receipt.payment.billing_period_start }} ~ {{ receipt.payment.billing_period_end }}</p>
    <p><strong>Payment Method:</strong> {{ receipt.payment.payment_method | upper }}</p>
    {% if receipt.payment.card_last4 %}
    <p><strong>Card:</strong> {{ receipt.payment.card_brand }} **** **** **** {{ receipt.payment.card_last4 }}</p>
    {% endif %}
    <p><strong>Transaction ID:</strong> {{ receipt.payment.transaction_id }}</p>
  </div>

  <div class="section">
    <h2>Itemized Charges (상세 내역)</h2>
    <table>
      <thead>
        <tr>
          <th>Description</th>
          <th>Qty</th>
          <th>Unit Price</th>
          <th>Amount</th>
          <th>Tax Rate</th>
        </tr>
      </thead>
      <tbody>
        {% for item in receipt.line_items %}
        <tr>
          <td>{{ item.description }}</td>
          <td>{{ item.quantity | format_number }}</td>
          <td>{{ item.unit_price | format_currency(item.currency) }}</td>
          <td>{{ item.amount | format_currency(item.currency) }}</td>
          <td>{{ (item.tax_rate * 100) | round }}%</td>
        </tr>
        {% endfor %}
      </tbody>
      <tfoot>
        <tr>
          <td colspan="3"></td>
          <td><strong>Subtotal (소계):</strong></td>
          <td>{{ receipt.summary.subtotal | format_currency(receipt.summary.currency) }}</td>
        </tr>
        <tr>
          <td colspan="3"></td>
          <td><strong>VAT (10%):</strong></td>
          <td>{{ receipt.summary.tax_total | format_currency(receipt.summary.currency) }}</td>
        </tr>
        <tr class="total-row">
          <td colspan="3"></td>
          <td><strong>Total:</strong></td>
          <td><strong>{{ receipt.summary.total | format_currency(receipt.summary.currency) }}</strong></td>
        </tr>
        <tr class="total-row">
          <td colspan="3"></td>
          <td><strong>Amount Paid:</strong></td>
          <td><strong>{{ receipt.summary.amount_paid | format_currency(receipt.summary.currency) }}</strong></td>
        </tr>
      </tfoot>
    </table>
  </div>

  <div class="section">
    <h2>Status (상태)</h2>
    <p><strong>Payment Status:</strong> <span style="color: green;">PAID ✓</span></p>
  </div>

  <div class="footer">
    <p><strong>DecisionOS Inc.</strong></p>
    <p>{{ receipt.issuer.address }}</p>
    <p>Business Number: {{ receipt.issuer.business_number }} | Email: {{ receipt.issuer.email }}</p>
    <hr>
    <p>Generated: {{ receipt.audit.generated_at | format_datetime }}</p>
    <p>Audit Link: <a href="{{ receipt.audit.audit_link }}">{{ receipt.audit.audit_link }}</a></p>
  </div>
</body>
</html>
```

---

### 4.2 Generation Workflow

```
1. Payment captured → Trigger receipt generation
2. Fetch data (payment, customer, invoice, line items)
3. Render HTML template (Jinja2)
4. Convert HTML → PDF (wkhtmltopdf)
5. Upload PDF to CDN (S3/CloudFront)
6. Store metadata in DB (receipts table)
7. Send email with PDF attachment
```

**Storage**:
- **Original JSON**: Store in DB (`receipts.json_data` column, JSONB)
- **PDF**: Store in S3 (`s3://receipts/{year}/{month}/{receipt_id}.pdf`)
- **Retention**: 7 years (compliance requirement)

---

## 5. Email Delivery

### 5.1 Email Template

**Subject**: `[DecisionOS] 결제가 완료되었습니다 (영수증 첨부) - Receipt {{ receipt_id }}`

**Body** (HTML):
```html
<p>안녕하세요, {{ customer_name }}님</p>

<p>DecisionOS 서비스 결제가 정상적으로 완료되었습니다.</p>

<h3>결제 정보</h3>
<ul>
  <li><strong>영수증 번호:</strong> {{ receipt_id }}</li>
  <li><strong>결제 금액:</strong> {{ total_amount | format_currency }}</li>
  <li><strong>결제일:</strong> {{ payment_date | format_date }}</li>
  <li><strong>청구 기간:</strong> {{ billing_period }}</li>
</ul>

<p>영수증 PDF는 첨부 파일로 제공되며, 아래 링크에서도 다운로드하실 수 있습니다:</p>
<p><a href="{{ pdf_download_link }}">영수증 다운로드</a></p>

<p>세금계산서가 필요하신 경우, 다음 달 10일까지 자동으로 발행되며 이메일로 발송됩니다.</p>

<hr>
<p><strong>문의:</strong> billing@decisionos.com | 1588-XXXX</p>
<p style="font-size: 12px; color: #999;">
  This is an automated message. Please do not reply directly to this email.
</p>
```

**Attachments**:
- `receipt-{{ receipt_id }}.pdf` (PDF file, ~100KB)

---

### 5.2 Multi-Language Support

**Supported Languages**:
- **Korean (ko)**: Default (primary market)
- **English (en)**: For international customers
- **Japanese (ja)**: Future support

**Detection**:
- Use customer's preferred language from account settings
- Fallback to browser language header (`Accept-Language`)
- Default to English if unsupported language

---

## 6. Security & Compliance

### 6.1 Access Control

**Who Can View Receipts**:
- ✅ **Account owner** (user who made payment)
- ✅ **Organization admins** (`billing_admin` role)
- ✅ **Finance/Auditor** (read-only, internal staff)
- ❌ **General users** (cannot view other org's receipts)

**API Authorization**:
```bash
GET /api/v1/receipts/R-2025-11-00123
Authorization: Bearer <token>

# Returns 200 OK if user has access, 403 Forbidden otherwise
```

---

### 6.2 Audit Trail

**Immutability**:
- Once generated, receipt **cannot be edited** (immutable record)
- Any corrections require generating a **new receipt** (e.g., refund receipt)

**Hash Verification**:
```python
import hashlib
import json

def verify_receipt(receipt_json):
    # Exclude hash and signature fields from hashing
    payload = {k: v for k, v in receipt_json.items() if k not in ['audit']}
    canonical = json.dumps(payload, sort_keys=True)
    computed_hash = hashlib.sha256(canonical.encode()).hexdigest()

    stored_hash = receipt_json['audit']['hash'].split(':')[1]
    return computed_hash == stored_hash
```

**Blockchain Anchoring** (Future):
- Hash of receipt stored on blockchain (public, tamper-proof)
- Allows independent verification without trusting DecisionOS

---

## 7. Localization (Korean-Specific)

### 7.1 Currency Formatting

**Korean Won (KRW)**:
- Format: `₩123,456` (currency symbol + comma separators)
- No decimal places (KRW is not subdivided)

**Multi-Currency**:
- If USD: `$123.45 USD` (2 decimal places)
- If EUR: `€123.45 EUR`

---

### 7.2 Date/Time Formatting

**Korean Standard**:
- Date: `2025년 11월 4일` (YYYY년 MM월 DD일)
- DateTime: `2025년 11월 4일 오후 2시 23분` (12-hour format with 오전/오후)

**ISO Format** (JSON):
- Always UTC: `2025-11-04T05:23:45Z`
- Display in KST (UTC+9) on PDF: `2025-11-04 14:23:45 KST`

---

### 7.3 Business Number Formatting

**Korean Business Number** (사업자등록번호):
- Format: `XXX-XX-XXXXX` (3-2-5 digits with hyphens)
- Example: `123-45-67890`

**Validation**:
- 10 digits total
- Checksum validation (last digit is check digit)

---

## 8. Error Handling

### 8.1 PDF Generation Failure

**Retry Logic**:
```
1. Initial attempt fails → Retry 2 times (exponential backoff: 5s, 15s)
2. If still failing → Alert engineering team, log error
3. Fallback: Send email with JSON receipt link (no PDF attachment)
```

**Customer Notification**:
- Email: "Your receipt is available online. PDF generation is delayed, please check back in 1 hour."
- Portal: Show "PDF generation in progress" status

---

### 8.2 Missing Data

**Required Fields Missing**:
- `customer_name` → Use `"Valued Customer"` placeholder
- `business_number` → Omit from receipt (not all customers have one)
- `line_items` empty → Error (cannot generate receipt without charges)

---

## 9. Testing & Validation

### 9.1 Test Cases

**Functional Tests**:
- [x] Payment receipt with single line item
- [x] Payment receipt with multiple line items (10+)
- [x] Refund receipt (partial refund)
- [x] Refund receipt (full refund)
- [x] Multi-currency (USD payment, KRW display)
- [x] Business customer (with VAT, business number)
- [x] Individual customer (no business number)

**Visual Tests**:
- [x] PDF renders correctly (no layout issues)
- [x] Korean characters display properly (font embedding)
- [x] Logo displays (image path correct)
- [x] Long descriptions wrap correctly (no overflow)

**Security Tests**:
- [x] Hash verification passes
- [x] Unauthorized users cannot access receipts (403 Forbidden)
- [x] PII redacted in logs (no full card numbers)

---

### 9.2 Sample Data

**Sample Payment Receipt** (JSON):
```json
{
  "receipt_id": "R-TEST-00001",
  "receipt_type": "payment",
  "customer": {
    "name": "김철수",
    "organization": "Test Corp",
    "business_number": "123-45-67890",
    "email": "test@example.com"
  },
  "payment": {
    "invoice_id": "INV-TEST-00001",
    "billing_period_start": "2025-11-01",
    "billing_period_end": "2025-11-30",
    "payment_method": "card",
    "card_brand": "Visa",
    "card_last4": "1234",
    "transaction_id": "ch_test_123"
  },
  "line_items": [
    {
      "description": "DecisionOS Pro Plan - Nov 2025",
      "quantity": 1,
      "unit_price": 100000,
      "amount": 100000,
      "currency": "KRW",
      "tax_rate": 0.10,
      "tax_amount": 10000
    }
  ],
  "summary": {
    "subtotal": 100000,
    "tax_total": 10000,
    "total": 110000,
    "amount_paid": 110000,
    "balance_due": 0,
    "currency": "KRW"
  },
  "status": "paid"
}
```

---

## 10. Related Documents

- [Payments Policy (Korean)](../docs/payments_policy_ko.md) — Payment terms, refund policy
- [KYC Notice (Korean)](../docs/kyc_notice_ko.md) — Customer verification, privacy
- [Settlement Runbook](../ops/runbook_settlement.md) — Settlement and reconciliation
- [Invoicing Guide](../docs/invoicing_guide.md) — Invoice generation (upstream of receipts)

---

## 11. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-04 | Finance Ops Team | Gate-U: Initial receipt template (PDF/JSON structure, Korean localization) |

---

**END OF DOCUMENT**
