# Settlement & Reconciliation Runbook — 정산 및 대사 운영 지침

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Owner**: Finance Operations Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This runbook provides operational procedures for:
- **Settlement processing** (PG → DecisionOS fund transfers)
- **Reconciliation** (matching internal ledger vs. PG settlement files)
- **Discrepancy resolution** (handling mismatches, missing transactions)
- **Fee accounting** (PG fees, FX fees, platform margins)
- **Reporting** (monthly financial close, audit support)

**Scope**: All payment gateways (PG) and payment methods (card, bank transfer, wire).

---

### 1.2 Key Concepts

| Term | Definition | Example |
|------|------------|---------|
| **Settlement (정산)** | Process where PG transfers collected funds to merchant (DecisionOS) | PG collects ₩100,000 → Transfers ₩98,000 to DecisionOS (after fees) |
| **Reconciliation (대사)** | Matching internal records against PG settlement files | Ledger shows 100 txns → PG file shows 99 txns → **1 mismatch** |
| **Ledger (원장)** | Internal accounting record of all transactions | `ledger_txns` table (charges, refunds, fees, payouts) |
| **Settlement File** | CSV/Excel file provided by PG with transaction details | Daily file from Stripe, monthly from KG Inicis |
| **PG Fee** | Fee charged by payment gateway | 2.9% + ₩300 per transaction |
| **Net Payout** | Amount actually transferred to merchant | Gross - PG Fee = Net Payout |

---

## 2. Settlement Cycle

### 2.1 Settlement Schedule

**By Payment Gateway**:

| PG Provider | Settlement Cycle | Transfer Day | File Delivery |
|-------------|------------------|--------------|---------------|
| **Stripe** | D+2 (rolling) | Daily | Automated API |
| **KG Inicis** | D+3 (rolling) | Daily (business days) | FTP upload (daily) |
| **NHN KCP** | D+7 (weekly batch) | Every Monday | Email attachment |
| **Toss Payments** | D+1 (next day) | Daily | Webhook + API |
| **Wire Transfer** | Manual (varies) | Confirmed via bank | N/A (manual entry) |

**Explanation**:
- **D+2**: Transaction captured on Day 0 → Settled on Day 2 (e.g., Mon captured → Wed settled)
- **Rolling**: Each day's transactions settle independently (not monthly batch)

---

### 2.2 Settlement Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Transactions Captured (D+0)                              │
│    • Customer payments processed                            │
│    • Recorded in ledger_txns (status: pending)              │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PG Processes Batch (D+1 ~ D+3)                           │
│    • PG aggregates transactions                             │
│    • Calculates fees, net payout                            │
│    • Initiates bank transfer                                │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Settlement File Generated (D+2 ~ D+7)                    │
│    • PG uploads file (FTP, API, email)                      │
│    • File contains: txn_id, amount, fee, net, date          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. DecisionOS Imports File (automated)                      │
│    • Cron job downloads file (daily at 06:00 UTC)           │
│    • Parses CSV/Excel → Inserts into settlement_batches     │
│    • Status: imported                                       │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Reconciliation (automated + manual review)               │
│    • Match ledger_txns vs settlement file                   │
│    • Flag discrepancies                                     │
│    • Generate recon report                                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Funds Received (D+3 ~ D+7)                               │
│    • Bank confirms wire transfer                            │
│    • Update ledger_txns (status: posted)                    │
│    • Close settlement batch                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Reconciliation Process

### 3.1 Reconciliation Goals

**Objectives**:
- ✅ **100% transaction match**: Every charge/refund in ledger should appear in PG file
- ✅ **Amount accuracy**: ± ₩100 tolerance (rounding differences)
- ✅ **Timeliness**: Recon completed within 24h of file receipt
- ✅ **Discrepancy rate**: ≤ 0.5% (target: 0.1%)

**Why Reconcile?**:
- Detect missing transactions (PG lost data, network failures)
- Catch duplicate charges (same txn charged twice)
- Verify fees (ensure PG not overcharging)
- Support audits (prove all revenue accounted for)

---

### 3.2 Daily Reconciliation Procedure

**Timing**: Every day at **07:00 UTC** (16:00 KST)

**Steps**:

#### Step 1: Import Settlement File

```bash
# Automated job (cron)
dosctl settlement import \
  --pg stripe \
  --date 2025-11-03 \
  --file s3://settlements/stripe/2025-11-03.csv

# Output:
# Imported 1,234 transactions
# Settlement batch ID: sb_2025_11_03_stripe
```

**Manual Import** (if automated job fails):
```bash
# Download file manually from PG portal
# Upload to staging area
dosctl settlement import \
  --pg inicis \
  --file /tmp/inicis_20251103.xlsx \
  --manual
```

---

#### Step 2: Run Reconciliation

```bash
dosctl settlement reconcile \
  --batch-id sb_2025_11_03_stripe \
  --output /reports/recon_2025-11-03.csv

# Output:
# Reconciliation Results:
#   Ledger Transactions: 1,250
#   Settlement File: 1,234
#   Matched: 1,230 (98.4%)
#   Unmatched Ledger: 20 (1.6%)
#   Unmatched PG File: 4 (0.3%)
#   Discrepancy Rate: 1.9% ❌ (exceeds 0.5% threshold)
```

**Automated Checks**:
1. **Count Match**: # of txns in ledger == # in PG file
2. **Amount Match**: Sum(ledger amounts) == Sum(PG file amounts)
3. **Transaction Match**: Each txn_id in ledger found in PG file

---

#### Step 3: Review Discrepancies

**Unmatched Transactions (Ledger)**:
```sql
-- Transactions in ledger but missing from PG file
SELECT
  txn_id,
  charge_id,
  amount,
  currency,
  created_at,
  status
FROM ledger_txns
WHERE
  created_at::date = '2025-11-03'
  AND txn_id NOT IN (SELECT txn_id FROM settlement_batches WHERE batch_id = 'sb_2025_11_03_stripe')
ORDER BY amount DESC;
```

**Common Causes**:
- ❌ **Pending transactions**: Not yet captured (still in `authorized` state)
- ❌ **Failed transactions**: Charge failed but still in ledger (status: `failed`)
- ❌ **Refunded before settlement**: Charge captured → Refunded same day → PG nets out (₩0)
- ❌ **PG timing mismatch**: Transaction captured 23:59 → Settled next day (shows in tomorrow's file)

**Action**:
- Check transaction status: `dosctl payments charges show {charge_id}`
- If pending/failed: **Expected**, mark as resolved
- If truly missing: **Escalate to PG support** (file dispute)

---

**Unmatched Transactions (PG File)**:
```sql
-- Transactions in PG file but missing from ledger
SELECT
  txn_id,
  amount,
  fee,
  net,
  settlement_date
FROM settlement_batches
WHERE
  batch_id = 'sb_2025_11_03_stripe'
  AND txn_id NOT IN (SELECT txn_id FROM ledger_txns WHERE created_at::date >= '2025-11-01')
ORDER BY amount DESC;
```

**Common Causes**:
- ❌ **Ledger write failure**: Charge succeeded but DB insert failed (rare, critical)
- ❌ **Duplicate in PG file**: PG bug (same txn listed twice)
- ❌ **Test transaction**: Sandbox transaction accidentally in production file

**Action**:
- Search wider date range: `WHERE created_at >= '2025-10-01'` (txn might be older)
- Check PG dashboard: Verify transaction actually exists
- If ledger missing: **Manual entry** (create ledger record, flag for audit)

---

#### Step 4: Resolve Discrepancies

**Small Discrepancies** (amount differences ≤ ₩100):
```sql
-- Flag as rounding difference (acceptable)
UPDATE settlement_batches
SET recon_status = 'matched_with_tolerance',
    recon_note = 'Rounding difference: ₩50 (FX conversion)'
WHERE batch_id = 'sb_2025_11_03_stripe'
  AND txn_id = 'ch_abc123'
  AND ABS(ledger_amount - settlement_amount) <= 100;
```

**Large Discrepancies** (> ₩100):
- **Investigate**: Check charge details, PG dashboard, customer invoice
- **Correct Ledger**: If ledger wrong, insert adjustment entry
  ```sql
  INSERT INTO ledger_txns (org_id, charge_id, type, amount, currency, status, note)
  VALUES ('org_123', 'ch_abc123', 'adjustment', -5000, 'KRW', 'posted', 'Recon adjustment: Refund not recorded');
  ```
- **Dispute with PG**: If PG wrong, file support ticket with evidence

---

#### Step 5: Generate Reconciliation Report

```bash
dosctl settlement report \
  --date 2025-11-03 \
  --format pdf \
  --output /reports/recon_2025-11-03.pdf

# Email to finance team
dosctl settlement report \
  --date 2025-11-03 \
  --email finance@decisionos.com
```

**Report Contents**:
- Summary: Total txns, matched %, discrepancy %
- Unmatched Ledger Transactions (table)
- Unmatched PG File Transactions (table)
- Amount Summary: Gross, Fees, Net, Expected vs Actual
- Action Items: List of transactions requiring manual review

---

### 3.3 Monthly Reconciliation

**Timing**: **5th business day of each month** (reconcile previous month)

**Additional Steps**:
1. **Aggregate Daily Recon**: Sum all daily reports for the month
2. **Cross-Check with Bank Statements**: Verify total payouts received
3. **Fee Audit**: Compare PG invoices vs calculated fees
4. **Variance Analysis**: Investigate any >₩10,000 variance
5. **Sign-Off**: Finance Manager approves monthly close

**Monthly Report Template**:
```
════════════════════════════════════════════════════════════
Monthly Reconciliation Report — October 2025
════════════════════════════════════════════════════════════

1. Transaction Summary
   Total Charges:        1,234 txns | ₩123,456,000
   Total Refunds:           56 txns | ₩5,600,000
   Net Revenue:                      | ₩117,856,000

2. Fee Summary
   PG Fees (2.9%):                   | ₩3,418,024
   FX Fees (1.5%):                   | ₩1,767,840
   Platform Margin:                  | ₩112,670,136

3. Settlement Summary
   Expected Payout:                  | ₩118,437,976
   Actual Payout (Bank):             | ₩118,420,000
   Variance:                         | -₩17,976 (0.015%)

4. Discrepancies
   Unmatched Ledger:     2 txns | ₩10,000 (resolved: pending refunds)
   Unmatched PG File:    1 txn  | ₩5,000 (resolved: PG duplicate entry)
   Amount Mismatches:    0 txns | ₩0

5. Status: ✅ PASSED (variance within ₩100,000 tolerance)

Approved by: Jane Doe (Finance Manager)
Date: 2025-11-05
════════════════════════════════════════════════════════════
```

---

## 4. Fee Accounting

### 4.1 Fee Types

**PG Fees** (Payment Gateway):
- **Percentage Fee**: 2.9% of transaction amount (Stripe)
- **Fixed Fee**: ₩300 per transaction (domestic cards)
- **Combined**: 2.9% + ₩300 (international cards)

**Example**:
```
Transaction: ₩100,000
PG Fee: (₩100,000 × 0.029) + ₩300 = ₩2,900 + ₩300 = ₩3,200
Net Payout: ₩100,000 - ₩3,200 = ₩96,800
```

---

**FX Fees** (Foreign Exchange):
- Charged when customer pays in USD but DecisionOS settles in KRW
- Typically **1.5% markup** over mid-market rate

**Example**:
```
Customer pays: $100 USD
FX rate (mid-market): 1,300 KRW/USD
FX rate (with markup): 1,280 KRW/USD (1.5% worse)
DecisionOS receives: $100 × 1,280 = ₩128,000 (vs ₩130,000 at mid-market)
FX Fee: ₩130,000 - ₩128,000 = ₩2,000 (1.5%)
```

---

**Platform Margin**:
- DecisionOS revenue after deducting all costs
- **Calculation**: `Margin = Customer Paid - COGS - PG Fee - FX Fee`

---

### 4.2 Fee Ledger Entries

**Recording Fees** (double-entry accounting):
```sql
-- When charge is captured
INSERT INTO ledger_txns (org_id, charge_id, type, amount, currency, status)
VALUES
  -- Revenue (customer paid)
  ('org_123', 'ch_abc', 'charge', 100000, 'KRW', 'posted'),

  -- PG Fee (expense)
  ('org_123', 'ch_abc', 'pg_fee', -3200, 'KRW', 'posted'),

  -- Net payout (cash flow)
  ('org_123', 'ch_abc', 'payout', 96800, 'KRW', 'posted');

-- Result: Ledger balanced (100,000 - 3,200 = 96,800)
```

---

## 5. Error Handling

### 5.1 Settlement File Missing

**Symptom**: Automated import job fails (no file found on FTP/API)

**Procedure**:
1. **Check PG Status Page**: Is PG experiencing downtime?
2. **Manual Download**: Login to PG portal, download file manually
3. **Contact PG Support**: If file >24h late, file support ticket
4. **Temporary Hold**: Freeze related invoices (don't send to customers)
5. **Retry**: Once file received, run manual import + recon

**Alert**:
```
🚨 Settlement File Missing — Stripe (2025-11-03)
Expected: 06:00 UTC, Current: 08:00 UTC (2h late)
Action: Check PG dashboard, manual download if available
```

---

### 5.2 High Discrepancy Rate

**Symptom**: Daily recon shows >1% discrepancy rate

**Procedure**:
1. **Immediate Investigation**: Don't wait, investigate same day
2. **Sample Unmatched Txns**: Pick top 10 by amount, investigate
3. **Pattern Analysis**: Are all unmatched from same time window? (Indicates batch issue)
4. **PG Escalation**: If systematic issue (e.g., all 23:00-23:59 txns missing), escalate to PG
5. **Daily Report**: Email finance team + oncall engineer

**Threshold**:
- **<0.5%**: Green (normal operations)
- **0.5%–1%**: Yellow (investigate, may be timing issue)
- **>1%**: Red (escalate to PG, halt invoicing if needed)

---

### 5.3 Duplicate Transactions

**Symptom**: Same `txn_id` appears twice in ledger or PG file

**Ledger Duplicate** (our bug):
```sql
-- Find duplicates
SELECT txn_id, COUNT(*)
FROM ledger_txns
WHERE created_at::date = '2025-11-03'
GROUP BY txn_id
HAVING COUNT(*) > 1;

-- Action: Delete duplicate entry, log incident
DELETE FROM ledger_txns
WHERE id = 12345 AND txn_id = 'ch_abc' AND created_at = (SELECT MAX(created_at) FROM ledger_txns WHERE txn_id = 'ch_abc');
```

**PG File Duplicate** (PG bug):
- Flag in recon report
- Email PG support with file + txn_id
- Do NOT double-count revenue (mark one entry as `duplicate`)

---

### 5.4 Negative Settlement (Net Refunds > Charges)

**Symptom**: Settlement file shows **negative payout** (we owe PG money)

**Scenario**:
- Day 1: ₩100,000 charges → Day 3: Settled (expect +₩97,000 payout)
- Day 2: ₩150,000 refunds → Day 4: Settled (expect -₩150,000 payout)
- Net Day 4: -₩53,000 (DecisionOS owes PG)

**Procedure**:
1. **Verify Refunds**: Ensure refunds are legitimate (check customer requests)
2. **Reserve Funds**: Ensure DecisionOS bank account has sufficient balance
3. **Process Debit**: PG will debit our account (or offset against future settlements)
4. **Update Ledger**: Record as `type: payout_reversal`

**Alert**:
```
⚠️ Negative Settlement — Stripe (2025-11-04)
Net Payout: -₩53,000 (refunds exceed charges)
Action: Verify refund legitimacy, ensure bank balance sufficient
```

---

## 6. Tools & Commands

### 6.1 dosctl Commands

**Import Settlement File**:
```bash
dosctl settlement import \
  --pg stripe \
  --date 2025-11-03 \
  --file s3://settlements/stripe/2025-11-03.csv
```

**Run Reconciliation**:
```bash
dosctl settlement reconcile \
  --batch-id sb_2025_11_03_stripe \
  --output /reports/recon_2025-11-03.csv
```

**Generate Report**:
```bash
dosctl settlement report \
  --date 2025-11-03 \
  --format pdf \
  --email finance@decisionos.com
```

**Check Discrepancies**:
```bash
dosctl settlement discrepancies \
  --date 2025-11-03 \
  --threshold 1000  # Only show discrepancies >₩1,000
```

**Manual Ledger Entry** (adjustment):
```bash
dosctl ledger adjust \
  --org org_123 \
  --charge ch_abc \
  --amount -5000 \
  --reason "Recon adjustment: Refund not recorded"
```

---

### 6.2 Database Queries

**Daily Settlement Summary**:
```sql
SELECT
  DATE(created_at) AS date,
  COUNT(*) AS txn_count,
  SUM(CASE WHEN type = 'charge' THEN amount ELSE 0 END) AS total_charges,
  SUM(CASE WHEN type = 'refund' THEN amount ELSE 0 END) AS total_refunds,
  SUM(CASE WHEN type = 'pg_fee' THEN amount ELSE 0 END) AS total_fees,
  SUM(CASE WHEN type = 'payout' THEN amount ELSE 0 END) AS net_payout
FROM ledger_txns
WHERE created_at >= '2025-11-01' AND created_at < '2025-12-01'
GROUP BY DATE(created_at)
ORDER BY date;
```

**Unmatched Transactions**:
```sql
-- See Step 3 in Section 3.2
```

**Fee Audit**:
```sql
SELECT
  pg,
  COUNT(*) AS txn_count,
  SUM(fee_calculated) AS fees_calculated,
  SUM(fee_actual) AS fees_actual,
  SUM(fee_actual - fee_calculated) AS variance
FROM (
  SELECT
    pg,
    amount * 0.029 + 300 AS fee_calculated,
    fee_amount AS fee_actual
  FROM settlement_batches
  WHERE settlement_date >= '2025-11-01' AND settlement_date < '2025-12-01'
) AS fee_audit
GROUP BY pg;
```

---

## 7. Alerts & Monitoring

### 7.1 Automated Alerts

**Settlement File Late** (>2h delay):
```yaml
alert: SettlementFileLate
severity: P2
trigger: |
  Expected file arrival: 06:00 UTC
  Current time: 08:00 UTC
  File not found: s3://settlements/stripe/2025-11-03.csv
action: |
  1. Check PG status page
  2. Manual download if available
  3. Alert finance team if >4h late
```

**High Discrepancy Rate** (>1%):
```yaml
alert: HighDiscrepancyRate
severity: P1
trigger: |
  Discrepancy rate: 2.5% (threshold: 1%)
  Unmatched txns: 25 (ledger) + 5 (PG file)
action: |
  1. Investigate top 10 unmatched by amount
  2. Check for timing issues (end-of-day cutoff)
  3. Escalate to PG if systematic
```

**Negative Settlement**:
```yaml
alert: NegativeSettlement
severity: P1
trigger: |
  Net payout: -₩53,000 (negative)
  Refunds: ₩150,000, Charges: ₩97,000
action: |
  1. Verify refund legitimacy
  2. Check bank balance (ensure funds available)
  3. Alert CFO if >₩1,000,000 debit
```

---

### 7.2 Dashboard Metrics

**Real-Time Metrics**:
- Pending settlements (awaiting PG transfer)
- Daily reconciliation status (pass/fail)
- Discrepancy rate (7-day rolling avg)
- Fee variance (expected vs actual)

**Historical Trends**:
- Monthly settlement volume (txn count, amount)
- PG fee trends (% of revenue)
- Discrepancy rate over time

---

## 8. Compliance & Audit

### 8.1 Audit Trail

**Immutability**:
- Once settlement batch is **posted**, it cannot be edited (immutable)
- Corrections via **adjustment entries** (new ledger txns with `type: adjustment`)

**Audit Logs**:
- All settlement imports logged: who, when, file URI, record count
- All manual adjustments logged: approver, reason, timestamp

**Retention**:
- Settlement files: **7 years** (regulatory requirement)
- Reconciliation reports: **7 years**
- Ledger txns: **Permanent** (soft delete only)

---

### 8.2 Monthly Close Checklist

- [ ] **All settlement files imported** (no missing days)
- [ ] **Daily recon completed** (0 pending)
- [ ] **Discrepancy rate ≤ 0.5%** (all exceptions documented)
- [ ] **Fee audit passed** (variance <1%)
- [ ] **Bank statement matched** (actual payouts == expected)
- [ ] **Finance Manager sign-off** (monthly report approved)
- [ ] **Data archived** (upload to long-term storage)

---

## 9. Escalation

### 9.1 When to Escalate

**To PG Support**:
- Settlement file missing >24h
- Systematic discrepancies (>10 txns in same pattern)
- Fee calculation error (>₩100,000 overcharge)
- Duplicate settlement (same batch twice)

**To Engineering Oncall**:
- Ledger write failures (txns missing from DB)
- Automated import job failing repeatedly (>3 consecutive days)
- Database corruption suspected

**To Finance Manager**:
- Monthly close delayed >3 days
- Discrepancy rate >5% (major issue)
- Negative settlement >₩5,000,000

**To CFO**:
- Fraud suspected (unauthorized refunds)
- PG dispute escalated to legal
- Regulatory audit request

---

### 9.2 Contact List

| Role | Name | Contact | Escalation Level |
|------|------|---------|------------------|
| **Finance Ops Lead** | Alice Kim | alice@decisionos.com, +82-10-1234-5678 | First |
| **Finance Manager** | Bob Lee | bob@decisionos.com | Second |
| **CFO** | Carol Park | carol@decisionos.com | Third (critical only) |
| **PG Support (Stripe)** | N/A | https://support.stripe.com | External |
| **PG Support (Inicis)** | N/A | support@inicis.com, 1588-XXXX | External |

---

## 10. Related Documents

- [Payments Policy (Korean)](../docs/payments_policy_ko.md) — Payment terms, refund policy
- [Chargeback Runbook](runbook_chargeback.md) — Dispute handling
- [Receipt Template](../templates/receipt_pdf.md) — Receipt generation (post-settlement)
- [Oncall Runbook](runbook_oncall.md) — General incident response

---

## 11. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-04 | Finance Ops Team | Gate-U: Initial settlement & reconciliation runbook |

---

**END OF DOCUMENT**
