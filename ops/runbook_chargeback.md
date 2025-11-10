# Chargeback & Dispute Runbook — 차지백 및 분쟁 대응 지침

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Owner**: Finance Operations + Customer Support
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This runbook provides procedures for handling:
- **Disputes** (고객 이의 제기): Customer contacts DecisionOS to dispute a charge
- **Chargebacks** (차지백): Customer bypasses DecisionOS and files dispute directly with card issuer
- **Evidence Collection** (증빙 수집): Gathering proof to defend against disputes
- **Win/Loss Outcomes** (승소/패소): Post-resolution actions

**Goal**: Minimize chargeback losses, protect revenue, maintain low dispute rate (<0.5%).

---

### 1.2 Terminology

| Term | Definition | Example |
|------|------------|---------|
| **Dispute (분쟁)** | Customer questions a charge validity | "I didn't authorize this payment" |
| **Chargeback (차지백)** | Customer requests refund via card issuer (not merchant) | Bank reverses ₩100,000 charge |
| **Chargeback Fee** | Fee charged by card network when chargeback filed | ₩15,000~₩30,000 per chargeback |
| **Retrieval Request** | Pre-chargeback: Issuer requests transaction proof | Issuer asks for receipt/invoice |
| **Chargeback Reason Code** | Standardized code explaining why chargeback filed | `10.4` (Fraud - Card Absent) |
| **Representment** | Merchant's response to chargeback (with evidence) | Submit invoice + usage logs |
| **Win** | Merchant successfully defends chargeback | Funds returned to merchant |
| **Loss** | Merchant fails to defend, funds permanently reversed | Merchant loses ₩100,000 + fee |

---

## 2. Chargeback Lifecycle

### 2.1 Stages

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Customer Files Chargeback                                │
│    • Customer contacts bank/card issuer                     │
│    • Claims: fraud, not received, defective, duplicate      │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Funds Immediately Reversed (D+0)                         │
│    • Issuer debits merchant account (DecisionOS)            │
│    • Customer receives provisional credit                   │
│    • Chargeback fee charged (₩15,000~₩30,000)               │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. DecisionOS Notified (D+1~D+3)                            │
│    • PG sends webhook: chargeback.created                   │
│    • Email alert to finance + support teams                 │
│    • Deadline to respond: 7~14 days (varies by network)     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Evidence Collection (D+1~D+7)                            │
│    • Pull transaction logs, invoices, customer emails       │
│    • Create HITL case (if customer contact needed)          │
│    • Prepare representment package                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Submit Representment (D+7)                               │
│    • Upload evidence to PG portal                           │
│    • PG forwards to issuing bank                            │
│    • Wait for issuer decision (30~90 days)                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Issuer Decision (D+30~D+90)                              │
│    • WIN: Funds returned to merchant + fee refunded         │
│    • LOSS: Funds permanently lost, fee stands               │
│    • PARTIAL: Split decision (rare)                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Post-Resolution Actions                                  │
│    • Update ledger (win: reverse chargeback, loss: write off)│
│    • Notify customer (win: explain decision, loss: close)   │
│    • Analyze root cause (prevent future chargebacks)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Chargeback Reason Codes

### 3.1 Visa Reason Codes

| Code | Description | Customer Claim | Winning Strategy |
|------|-------------|----------------|------------------|
| **10.4** | Fraud - Card Absent Environment | "I didn't make this purchase" | Prove IP match, device fingerprint, prior successful txns |
| **13.1** | Services Not Provided | "I paid but didn't receive service" | Show service usage logs (API calls, logins, data downloads) |
| **13.2** | Canceled Recurring | "I canceled but was still charged" | Show cancellation request date vs charge date (if after, win) |
| **13.3** | Not as Described | "Service quality poor" | Show terms of service, usage agreement, no SLA breach |
| **13.6** | Credit Not Processed | "I requested refund but didn't get it" | Show refund was processed (bank statement, refund receipt) |
| **13.7** | Canceled Merchandise | "I canceled order before delivery" | Show cancellation policy, delivery before cancellation |
| **30** | Services Not as Described | "Service doesn't match description" | Show accurate marketing materials, feature list |
| **57** | Fraudulent Transaction | "My card was stolen" | Hardest to win (customer may be victim); verify fraud patterns |

---

### 3.2 Mastercard Reason Codes

| Code | Description | Customer Claim | Winning Strategy |
|------|-------------|----------------|------------------|
| **4837** | No Cardholder Authorization | "I didn't authorize this" | Prove customer initiated (IP, email confirmation, usage) |
| **4853** | Defective/Not as Described | "Service doesn't work" | Show uptime logs, support tickets resolved, no SLA breach |
| **4855** | Goods/Services Not Provided | "I paid but got nothing" | Usage logs (prove customer used service) |
| **4860** | Credit Not Processed | "Refund promised but not received" | Show refund transaction, bank processing time explanation |
| **4863** | Cardholder Does Not Recognize | "I don't remember this charge" | Provide descriptor (how charge appears on statement), invoice |

---

### 3.3 Common Reasons (DecisionOS Context)

**Most Common**:
1. **"Service Not Provided"** (40% of chargebacks)
   - Reality: Customer used service but forgot or wants free usage
   - Defense: API call logs, dashboard login timestamps, data exported

2. **"Fraud - Card Not Present"** (30%)
   - Reality: May be true fraud OR customer remorse
   - Defense: IP geolocation match, email verification, 2FA logs

3. **"Canceled Subscription"** (20%)
   - Reality: Customer canceled but was charged for current cycle
   - Defense: Cancellation policy (charge for current month, refund next)

4. **"Not as Described"** (10%)
   - Reality: Customer misunderstood features or had unrealistic expectations
   - Defense: Marketing materials, trial period usage, support tickets

---

## 4. Response Procedures

### 4.1 Initial Alert (Within 1 Hour)

**Webhook Received**:
```json
{
  "event": "chargeback.created",
  "chargeback_id": "cb_1A2B3C4D",
  "charge_id": "ch_xyz789",
  "amount": 100000,
  "currency": "KRW",
  "reason_code": "13.1",
  "reason": "Services Not Provided",
  "due_date": "2025-11-18T23:59:59Z",
  "status": "needs_response"
}
```

**Automated Actions**:
1. **Reverse Funds**: Update ledger (`type: chargeback`, `amount: -100000`)
2. **Charge Fee**: Record chargeback fee (`type: chargeback_fee`, `amount: -20000`)
3. **Create HITL Case**: Auto-generate case in HITL queue (`priority: P1`, `category: chargeback`)
4. **Alert Teams**: Email to `finance@`, `support@`, Slack `#chargebacks`

**Manual Actions** (within 1h):
- [ ] Assign case to **Chargeback Specialist** (or finance lead if no specialist)
- [ ] Review charge details (customer, amount, date, invoice)
- [ ] Initial triage: **Winnable?** (see Section 4.2)

---

### 4.2 Triage Decision (Within 4 Hours)

**Winnable Chargebacks** (fight):
- ✅ Clear evidence of service delivery (usage logs, support interactions)
- ✅ Customer has history of successful payments (not first txn)
- ✅ Amount >₩100,000 (worth the effort)
- ✅ Reason code we typically win (see Section 3)

**Unwinnable Chargebacks** (accept loss):
- ❌ True fraud (card stolen, customer reports to police)
- ❌ No usage logs (customer never logged in, no API calls)
- ❌ SLA breach (we failed to deliver service per contract)
- ❌ Amount <₩50,000 (cost of fighting > potential recovery)

**Decision Matrix**:

| Amount | Evidence Quality | Historical Win Rate | Decision |
|--------|------------------|---------------------|----------|
| >₩500K | Strong | >70% | **Fight** (high-value) |
| ₩100K–₩500K | Strong | >70% | **Fight** (good odds) |
| ₩100K–₩500K | Weak | <50% | **Accept** (likely to lose) |
| <₩100K | Any | Any | **Accept** (not cost-effective unless pattern) |

---

### 4.3 Evidence Collection (Within 7 Days)

**Standard Evidence Package**:

#### 1. Transaction Proof
```
• Invoice (PDF + link to customer portal)
• Payment receipt (with transaction ID, timestamp)
• Email confirmation sent to customer (after payment)
```

#### 2. Service Delivery Proof
```
• Usage logs:
  - API call timestamps (prove customer used service)
  - Dashboard login timestamps (prove customer accessed platform)
  - Data exports/downloads (prove customer consumed service)

• Example log snippet:
  2025-10-15 09:23:45 UTC | API Call | POST /api/v1/decisions | IP: 123.45.67.89
  2025-10-20 14:12:30 UTC | Login    | Dashboard accessed      | IP: 123.45.67.89
  2025-10-25 16:45:12 UTC | Export   | Downloaded 5,000 records | IP: 123.45.67.89
```

#### 3. Customer Communication
```
• Email thread (customer support tickets, feature requests)
• Chat logs (if customer contacted support, shows awareness of charge)
• Terms of Service acceptance (timestamp, IP address)
```

#### 4. Fraud Prevention (if fraud claim)
```
• IP geolocation (match customer's known location)
• Device fingerprint (same device as previous successful txns)
• Email verification log (customer verified email after signup)
• 2FA logs (if enabled, proves customer authenticated)
```

#### 5. Refund Policy
```
• Cancellation policy (if customer claims they requested refund)
• Refund request timestamp (if later than charge, customer at fault)
• Refund processing timeline (if within policy, merchant did nothing wrong)
```

---

**Evidence Checklist Template**:
```markdown
# Chargeback Evidence — Case CB-2025-11-001

**Charge Details**:
- Charge ID: ch_xyz789
- Amount: ₩100,000
- Date: 2025-10-01
- Customer: hong@example.com (Org: TestCorp)
- Reason: 13.1 (Services Not Provided)

**Evidence Submitted**:
- [x] Invoice (INV-2025-10-00123) — PDF attached
- [x] Payment receipt (R-2025-10-00456) — PDF attached
- [x] Usage logs (Oct 1–31) — CSV attached (500 API calls)
- [x] Email confirmation (payment success) — Oct 1, 10:23 UTC
- [x] Customer support tickets (2 tickets, both resolved) — Screenshots attached
- [x] Terms of Service acceptance — Oct 1, 10:15 UTC, IP 123.45.67.89
- [x] Cancellation policy — Clearly states "no refunds for partial month"

**Narrative** (to issuing bank):
"Customer signed up on Oct 1, 2025, and actively used our API service throughout
October (500 API calls documented). Customer accessed dashboard 15 times and
downloaded data on Oct 25. Customer also contacted support twice with feature
requests, demonstrating awareness and use of service. Payment was authorized
and charged on Oct 31 per billing cycle. Customer's claim of 'service not provided'
is contradicted by extensive usage logs. We respectfully request chargeback be
reversed."

**Attachments**: 8 files, 2.3MB total
**Submitted by**: Alice Kim (Finance Ops)
**Submitted on**: 2025-11-05 (within 7-day deadline)
```

---

### 4.4 Submit Representment (Day 7)

**Submission Methods**:

**Via PG Portal** (Stripe, Toss):
1. Login to PG dashboard
2. Navigate to "Disputes" → Select chargeback
3. Upload evidence files (max 10MB per file, PDF/JPG/PNG)
4. Write narrative (max 5,000 characters)
5. Click "Submit Response"
6. Receive confirmation email

**Via Email** (Inicis, KCP):
1. Compile evidence into single ZIP file
2. Email to `disputes@{pg}.com` with subject: `Chargeback Response - {charge_id}`
3. Include case number in body
4. Request read receipt

**Via API** (automated, if supported):
```bash
dosctl chargeback respond \
  --chargeback-id cb_1A2B3C4D \
  --evidence /evidence/cb-2025-11-001.zip \
  --narrative "Customer used service extensively (500 API calls). See logs attached."
```

---

## 5. Post-Decision Actions

### 5.1 Win (Merchant Prevails)

**Outcome**: Funds returned to merchant, chargeback fee refunded

**Actions**:
1. **Update Ledger**:
   ```sql
   INSERT INTO ledger_txns (org_id, charge_id, type, amount, status)
   VALUES
     ('org_123', 'ch_xyz', 'chargeback_reversal', 100000, 'posted'),  -- Funds restored
     ('org_123', 'ch_xyz', 'chargeback_fee_refund', 20000, 'posted'); -- Fee refunded
   ```

2. **Notify Customer** (optional, if want to maintain relationship):
   ```
   Subject: [DecisionOS] Payment Dispute Resolved

   Dear Customer,

   The recent payment dispute you filed has been reviewed by your card issuer.
   Based on the evidence provided (service usage logs, invoices), the dispute
   was resolved in favor of DecisionOS. The charge of ₩100,000 will remain on
   your statement.

   If you have any questions or concerns about your service, please contact
   our support team directly rather than disputing charges.

   Thank you,
   DecisionOS Finance Team
   ```

3. **Analyze Root Cause**:
   - Why did customer file chargeback instead of contacting support?
   - Was billing descriptor confusing? (e.g., "DECISIONOS*API" vs clear name)
   - Was cancellation policy clear during signup?

4. **Celebrate** (if first win or high-value):
   - Share in `#finance` Slack: "Won ₩500K chargeback! Great evidence collection."

---

### 5.2 Loss (Merchant Loses)

**Outcome**: Funds permanently reversed, chargeback fee stands, merchant loses ₩120,000 total

**Actions**:
1. **Update Ledger**:
   ```sql
   -- Funds already reversed on Day 0 (chargeback created)
   -- No further ledger entries needed
   UPDATE ledger_txns
   SET status = 'chargeback_lost'
   WHERE charge_id = 'ch_xyz' AND type = 'chargeback';
   ```

2. **Write Off**:
   - Mark as bad debt (accounting)
   - If amount >₩1M, report to CFO

3. **Customer Account Review**:
   - **Suspend account** (if fraud suspected or repeat offender)
   - **Blacklist** (prevent future signups with same card/email)
   - **Fraud score** (flag customer profile)

4. **Root Cause Analysis**:
   - **True fraud**: Tighten fraud detection (e.g., require 2FA for new accounts)
   - **Service not delivered**: Fix service delivery (ensure customers know how to use)
   - **Confusing billing**: Improve descriptor, send reminder emails before charge
   - **Customer remorse**: Improve onboarding, trial period, clearer cancellation policy

5. **Pattern Detection**:
   ```sql
   -- Find customers with multiple chargebacks
   SELECT customer_id, COUNT(*) AS chargeback_count
   FROM ledger_txns
   WHERE type = 'chargeback' AND status = 'chargeback_lost'
   GROUP BY customer_id
   HAVING COUNT(*) > 1
   ORDER BY chargeback_count DESC;
   ```

---

## 6. Prevention Strategies

### 6.1 Pre-Transaction

**Fraud Detection**:
- **IP Geolocation**: Block high-risk countries (if not your market)
- **Email Verification**: Require email confirmation before first charge
- **Card BIN Check**: Flag prepaid cards, gift cards (higher fraud risk)
- **Velocity Limits**: Max 3 failed payment attempts per hour (prevent card testing)

**Clear Communication**:
- **Billing Descriptor**: Use recognizable name (e.g., "DECISIONOS.COM API SERVICE" not "ACME CORP")
- **Pre-Charge Email**: "Your card will be charged ₩100,000 on Oct 31" (3 days before)
- **Trial Period**: 7-day free trial reduces "buyer's remorse" chargebacks

---

### 6.2 During Transaction

**Strong Authentication**:
- **3D Secure (3DS)**: Shifts liability to issuer (if customer authenticated, bank can't chargeback)
- **2FA**: Require 2FA for account creation (proves customer identity)
- **CVC Check**: Decline if CVC doesn't match (reduces stolen card usage)

**Usage Tracking**:
- **Log Everything**: API calls, logins, downloads (evidence for disputes)
- **Automated Emails**: "You made 500 API calls today" (proves customer used service)

---

### 6.3 Post-Transaction

**Proactive Support**:
- **Email Surveys**: "How was your experience?" (catch dissatisfaction before chargeback)
- **Easy Refund Process**: "Click here to request refund" (cheaper than chargeback)
- **Fast Response**: Answer support tickets within 4h (prevent frustration)

**Clear Cancellation**:
- **Self-Service**: Let customers cancel instantly (don't require email to support)
- **Confirmation Email**: "Your subscription is canceled, final charge on Oct 31" (clear)
- **Refund Policy**: "No refunds for partial month, but you can use until Nov 1" (fair + clear)

---

## 7. Metrics & KPIs

### 7.1 Chargeback Rate

**Formula**:
```
Chargeback Rate = (# of Chargebacks) / (# of Transactions) × 100
```

**Thresholds**:
- **<0.5%**: Green (normal, acceptable)
- **0.5%–1.0%**: Yellow (monitor closely, investigate causes)
- **>1.0%**: Red (excessive, risk of PG penalties or account termination)

**Industry Benchmark**: SaaS companies typically see 0.2%–0.5%.

---

### 7.2 Win Rate

**Formula**:
```
Win Rate = (# of Wins) / (# of Chargebacks Fought) × 100
```

**Target**: ≥60% (means good evidence collection)

**By Reason Code** (track separately):
- Fraud (10.4, 4837): 20–40% win rate (hardest to win)
- Service Not Provided (13.1): 60–80% (if you have logs)
- Not as Described (13.3): 40–60% (subjective)

---

### 7.3 Financial Impact

**Monthly Report**:
```
════════════════════════════════════════════════════════════
Chargeback Report — October 2025
════════════════════════════════════════════════════════════

Transactions:           10,000 txns | ₩1,000,000,000
Chargebacks Filed:         20 txns | ₩2,000,000 (0.2% rate ✅)
Chargeback Fees:           20 × ₩20,000 = ₩400,000

Fought:                    15 chargebacks
Won:                        9 (60% win rate ✅)
Lost:                       6 (40%)

Financial Impact:
  Funds Lost (6 losses): ₩1,200,000
  Fees (non-refundable): ₩120,000 (6 losses × ₩20K)
  Total Loss:            ₩1,320,000 (0.13% of revenue)

Funds Recovered (9 wins): ₩800,000
Net Loss:                 ₩520,000 (0.05% of revenue)

Accepted without Fight:    5 chargebacks | ₩200,000
  Reason: All <₩50K (not cost-effective)

Top Reasons:
  1. Service Not Provided (13.1): 8 cases (40%)
  2. Fraud (10.4): 6 cases (30%)
  3. Canceled Recurring (13.2): 4 cases (20%)
  4. Other: 2 cases (10%)

Action Items:
  - Improve billing descriptor (3 customers said "didn't recognize")
  - Add pre-charge reminder email (reduce "forgot" chargebacks)
  - Strengthen fraud detection (6 fraud cases, 2 confirmed stolen cards)
════════════════════════════════════════════════════════════
```

---

## 8. Tools & Automation

### 8.1 dosctl Commands

**List Chargebacks**:
```bash
dosctl chargeback list \
  --status needs_response \
  --sort-by due_date

# Output:
# ID              Charge         Amount    Reason                Due Date
# cb_1A2B3C4D     ch_xyz789      ₩100,000  Services Not Provided 2025-11-18
# cb_2B3C4D5E     ch_abc456      ₩200,000  Fraud - CNP           2025-11-20
```

**Get Details**:
```bash
dosctl chargeback show cb_1A2B3C4D

# Output:
# Chargeback ID: cb_1A2B3C4D
# Charge ID: ch_xyz789
# Amount: ₩100,000
# Reason: 13.1 (Services Not Provided)
# Filed: 2025-11-04
# Due: 2025-11-18 (14 days to respond)
# Status: needs_response
# Customer: hong@example.com (Org: TestCorp)
```

**Submit Response**:
```bash
dosctl chargeback respond \
  --chargeback-id cb_1A2B3C4D \
  --evidence /evidence/cb-001.zip \
  --narrative "Customer used service extensively..."
```

**Check Win/Loss**:
```bash
dosctl chargeback stats --month 2025-10

# Output:
# Chargebacks: 20 (0.2% rate)
# Won: 9 (60%)
# Lost: 6 (40%)
# Pending: 5
# Total Loss: ₩520,000
```

---

### 8.2 Automated Evidence Collection

**Script** (`collect_chargeback_evidence.py`):
```python
def collect_evidence(charge_id):
    """Auto-collect evidence for chargeback defense."""

    # 1. Fetch charge details
    charge = db.query("SELECT * FROM charges WHERE id = %s", [charge_id])
    customer = db.query("SELECT * FROM customers WHERE id = %s", [charge.customer_id])

    # 2. Generate invoice PDF
    invoice_pdf = generate_invoice_pdf(charge.invoice_id)

    # 3. Pull usage logs (API calls, logins)
    usage_logs = db.query("""
        SELECT timestamp, event_type, ip_address
        FROM audit_logs
        WHERE org_id = %s AND timestamp >= %s AND timestamp <= %s
        ORDER BY timestamp
    """, [customer.org_id, charge.billing_period_start, charge.billing_period_end])

    # 4. Pull support tickets
    tickets = db.query("""
        SELECT subject, created_at, status
        FROM support_tickets
        WHERE org_id = %s AND created_at <= %s
        ORDER BY created_at
    """, [customer.org_id, charge.created_at])

    # 5. Compile evidence package
    evidence = {
        "invoice_pdf": invoice_pdf,
        "usage_logs_csv": export_to_csv(usage_logs),
        "support_tickets_pdf": generate_tickets_pdf(tickets),
        "tos_acceptance": get_tos_acceptance_log(customer.org_id)
    }

    # 6. Upload to S3
    s3_uri = upload_to_s3(evidence, f"chargebacks/{charge_id}/evidence.zip")

    return s3_uri
```

---

## 9. Escalation

### 9.1 When to Escalate

**To Finance Manager**:
- High-value chargeback (>₩1,000,000)
- Pattern detected (same customer, 3+ chargebacks)
- Win rate drops below 50% (process issue?)

**To Legal**:
- Customer makes false fraud claim (provable)
- Consider pursuing legal action (if >₩10,000,000 loss)
- PG threatens account termination (excessive chargeback rate)

**To CFO**:
- Monthly chargeback loss >₩10,000,000
- Chargeback rate >1.0% (risk of PG penalties)

---

## 10. Related Documents

- [Payments Policy (Korean)](../docs/payments_policy_ko.md) — Refund policy, dispute process (customer-facing)
- [Settlement Runbook](runbook_settlement.md) — Settlement reconciliation (includes chargeback accounting)
- [HITL Operations Runbook](runbook_hitl_ops.md) — HITL case management (chargebacks auto-create cases)
- [Oncall Runbook](runbook_oncall.md) — General incident response

---

## 11. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-04 | Finance Ops Team | Gate-U: Initial chargeback & dispute runbook |

---

**END OF DOCUMENT**
