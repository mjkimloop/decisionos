# Cost Guard Runbook — 원가 관리 및 마진 최적화 운영 지침

**Version**: 1.0.0
**Last Updated**: 2025-11-03
**Owner**: Finance Operations + Product Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

**Cost Guard** monitors cloud costs, model inference costs, and revenue to ensure healthy **profit margins**. This runbook covers:
- **Cost tracking** (cloud infra, ML models, third-party APIs)
- **Margin calculation** (revenue - costs = profit)
- **Alerts** (margin below target, cost spikes)
- **Optimization actions** (pricing adjustments, quota limits, feature gating)

**Goal**: Maintain **≥40% profit margin** per organization/product.

---

### 1.2 Key Concepts

| Term | Definition | Example |
|------|------------|---------|
| **COGS (Cost of Goods Sold)** | Direct costs to deliver service | Cloud compute, ML API fees |
| **Revenue** | Amount billed to customer | ₩100,000/month subscription |
| **Margin** | `(Revenue - COGS) / Revenue × 100` | (₩100K - ₩60K) / ₩100K = 40% |
| **Unit Economics** | Cost/revenue per unit (e.g., per decision call) | Cost: ₩1.5/call, Revenue: ₩2/call → 25% margin |

---

## 2. Cost Sources

### 2.1 Infrastructure Costs

**Cloud Providers** (AWS, GCP, Azure):
- **Compute**: EC2/GCE instances, Kubernetes pods
- **Storage**: S3, GCS (data lake, backups)
- **Database**: RDS, Cloud SQL (PostgreSQL)
- **Networking**: Data transfer (egress)

**Cost Feed**:
```yaml
infra_costs:
  - resource: s3_storage
    unit: gb_month
    cost_per_unit: 0.023  # USD per GB/month

  - resource: compute_seconds
    unit: cpu_sec
    cost_per_unit: 0.0001  # USD per CPU-second

  - resource: rds_postgres
    unit: instance_hour
    cost_per_unit: 0.15    # USD per hour (db.m5.large)
```

---

### 2.2 Model Inference Costs

**Third-Party ML APIs**:
- OpenAI GPT (for text generation): $0.002/1K tokens
- AWS SageMaker (custom models): $0.05/1K predictions

**Cost Feed**:
```yaml
model_costs:
  - model_id: openai_gpt4
    unit: tokens
    cost_per_unit: 0.000002  # USD per token

  - model_id: sagemaker_credit_model
    unit: decision_call
    cost_per_unit: 0.0005    # USD per call
```

---

### 2.3 Third-Party Services

- **PG Fees**: 2.9% + $0.30 per transaction
- **KYC Provider**: $0.50 per verification
- **SMS/Email**: $0.01 per SMS, $0.001 per email

---

## 3. Margin Calculation

### 3.1 Formula

```
Revenue (month) = Base Fee + Overage Charges
COGS (month) = Infra Costs + Model Costs + Third-Party Fees
Profit = Revenue - COGS
Margin (%) = (Profit / Revenue) × 100
```

**Example**:
```
Org: TestCorp (Pro plan)

Revenue:
  Base Fee: ₩100,000
  Overage (2,000 decisions × ₩2): ₩4,000
  Total Revenue: ₩104,000

COGS:
  Compute: ₩15,000
  Storage: ₩5,000
  ML API (OpenAI): ₩20,000
  PG Fees: ₩3,000
  Total COGS: ₩43,000

Profit: ₩104,000 - ₩43,000 = ₩61,000
Margin: (₩61,000 / ₩104,000) × 100 = **58.7%** ✅ (above 40% target)
```

---

### 3.2 Unit Economics

**Per Decision Call**:
```
Revenue: ₩2 per call (overage rate)
Cost:
  Compute: ₩0.50
  ML API: ₩1.00
  Total Cost: ₩1.50

Unit Margin: (₩2 - ₩1.50) / ₩2 = 25%
```

**Analysis**: 25% margin is below target (40%). **Action**: Increase price to ₩2.50 OR reduce ML API usage.

---

## 4. Alerts & Thresholds

### 4.1 Margin Alerts

**Thresholds**:

| Margin | Severity | Action |
|--------|----------|--------|
| **≥60%** | 🟢 Green | Excellent (consider lowering prices to gain market share) |
| **40%-60%** | 🟡 Yellow | Healthy (monitor) |
| **20%-40%** | 🟠 Orange | Warning (optimize costs or raise prices) |
| **<20%** | 🔴 Red | Critical (immediate action required) |

**Alert Example**:
```yaml
alert: LowMargin
severity: P1
trigger: |
  org_id: org_abc123
  margin: 18% (below 20% threshold)
  revenue: ₩100,000
  cogs: ₩82,000
action: |
  1. Review cost breakdown (which component is highest?)
  2. Consider:
     - Increase base fee (₩100K → ₩120K)
     - Reduce quota (5,000 → 3,000 decisions/day)
     - Gate expensive features (ML models → basic only)
  3. Notify product team for pricing review
```

---

### 4.2 Cost Spike Alerts

**Trigger**: Month-over-month cost increase >30%

**Example**:
```
Nov COGS: ₩50,000
Dec COGS: ₩70,000 (+40%) ⚠️

Root Cause Analysis:
  - Compute cost spiked from ₩15K → ₩30K (2x)
  - Reason: New customer with 10x usage, no quota limit set

Action:
  - Set hard quota for new customer (5,000 decisions/day → enforce)
  - Investigate: Is usage legitimate or abuse?
```

---

## 5. Optimization Actions

### 5.1 Pricing Adjustments

**Scenario**: Margin drops below 40% across multiple orgs.

**Actions**:
1. **Increase Base Fee**: ₩100,000 → ₩120,000 (20% increase)
   - Impact: Immediate margin boost, but risk customer churn
   - Rollout: 30-day notice, grandfather existing customers for 6 months

2. **Increase Overage Rates**: ₩2/call → ₩2.50/call
   - Impact: High-usage customers pay more (fair, usage-based)
   - Rollout: 30-day notice

3. **Introduce Tiers**: Add "Pro Plus" plan (₩150,000, higher quotas)
   - Impact: Upsell high-usage customers, improve margin

---

### 5.2 Quota Limits

**Scenario**: Customer using excessive ML API calls (high cost).

**Actions**:
1. **Reduce Quota**: 5,000 decisions/day → 3,000 decisions/day
   - Impact: Forces customer to upgrade to Enterprise (negotiated pricing)

2. **Hard Limit on Expensive Features**:
   ```yaml
   decisions.run.ml:
     quota_per_day: 1000  # Limit ML decisions
     fallback: decisions.run.basic  # Use rule-based instead
   ```

3. **Throttle High-Cost APIs**:
   - Detect: Customer making 10K OpenAI API calls/day (cost: ₩20K/day)
   - Action: Email customer: "Your usage is unusually high. Consider optimizing?"

---

### 5.3 Feature Gating

**Scenario**: Free plan users consuming too much compute.

**Actions**:
1. **Restrict Features**:
   - Free plan: Disable ML models (only allow rule-based decisions)
   - Pro plan: Limit ML to 1,000 calls/day

2. **Sunset Loss-Making Features**:
   - If "custom model uploads" cost ₩50K/month but generate ₩10K revenue → Deprecate feature OR charge ₩100K/month

---

### 5.4 Cost Optimization

**Cloud Costs**:
- **Reserved Instances**: Save 30-50% on compute (commit to 1-3 years)
- **Spot Instances**: Save 70% on non-critical workloads (batch jobs)
- **Auto-Scaling**: Scale down during off-peak hours (nights, weekends)
- **S3 Lifecycle**: Move old data to Glacier (90% cheaper)

**ML Costs**:
- **Model Compression**: Use smaller models (GPT-3.5 vs GPT-4, 10x cheaper)
- **Caching**: Cache ML predictions (avoid duplicate calls)
- **Batching**: Batch API requests (some providers give volume discounts)

---

## 6. Dashboard & Reports

### 6.1 Real-Time Dashboard

**URL**: `/ops/cost-guard`

**Panels**:
- **Margin by Org** (sorted, lowest margin first)
- **Cost Breakdown** (pie chart: Compute, Storage, ML, Third-Party)
- **Revenue vs COGS Trend** (line chart, 6 months)
- **Top 10 High-Cost Orgs** (table)

**Example**:
```
Org              Revenue   COGS      Margin
───────────────────────────────────────────────
org_abc123       ₩100K     ₩82K      18% 🔴
org_xyz789       ₩200K     ₩80K      60% 🟢
org_def456       ₩150K     ₩90K      40% 🟡
```

---

### 6.2 Monthly Report

**Template**:
```
════════════════════════════════════════════════════════════
Cost Guard Report — November 2025
════════════════════════════════════════════════════════════

1. Summary
   Total Revenue:       ₩10,000,000
   Total COGS:          ₩5,500,000
   Total Profit:        ₩4,500,000
   Overall Margin:      45% ✅ (target: 40%)

2. Cost Breakdown
   Compute:             ₩2,000,000 (36%)
   Storage:             ₩800,000 (15%)
   ML APIs:             ₩1,500,000 (27%)
   Third-Party:         ₩1,200,000 (22%)

3. High-Risk Orgs (Margin <20%)
   - org_abc123: 18% (Action: Increase price to ₩120K)
   - org_ghi789: 15% (Action: Reduce quota or gate ML features)

4. Cost Optimization Actions
   - Migrated 500 GB to S3 Glacier (saved ₩200,000/month)
   - Enabled auto-scaling (reduced idle compute by 30%)

5. Pricing Changes
   - Increased base fee: ₩100K → ₩120K (effective Dec 1)
   - Increased overage rate: ₩2 → ₩2.50 (effective Dec 1)

Approved by: Finance Manager
════════════════════════════════════════════════════════════
```

---

## 7. Escalation

### 7.1 When to Escalate

**To Product Team**:
- Margin <40% across multiple orgs (systemic pricing issue)
- Feature costs exceed revenue (consider deprecation)

**To Finance Manager**:
- Overall margin <30% (company-wide issue)
- Need approval for major pricing changes (>20% increase)

**To CTO/CEO**:
- Margin <10% (severe issue, unsustainable)
- Major strategic decision (sunset product, pivot pricing model)

---

## 8. Tools & Commands

### 8.1 dosctl Commands

**Check Margin**:
```bash
dosctl ops cost-guard --org org_abc123 --period 2025-11

# Output:
# Org: org_abc123
# Revenue: ₩100,000
# COGS: ₩82,000
# Margin: 18% 🔴 (below 20% threshold)
```

**Cost Breakdown**:
```bash
dosctl ops cost-breakdown --org org_abc123 --period 2025-11

# Output:
# Compute: ₩30,000 (37%)
# Storage: ₩10,000 (12%)
# ML APIs: ₩40,000 (49%)
# Third-Party: ₩2,000 (2%)
```

**Set Alert**:
```bash
dosctl ops cost-alert set \
  --org org_abc123 \
  --threshold 20 \
  --action email:finance@decisionos.com
```

---

## 9. Related Documents

- [Plans & Entitlements](../docs/plans_and_entitlements.md) — Pricing details
- [Billing Terms (Korean)](../docs/billing_terms_ko.md) — Customer-facing billing
- [Settlement Runbook](runbook_settlement.md) — Revenue reconciliation

---

## 10. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-03 | Finance Ops + Product Team | Gate-S: Initial Cost Guard runbook (margin tracking, optimization) |

---

**END OF DOCUMENT**
