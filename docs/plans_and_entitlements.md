# Plans & Entitlements Policy — 요금제 및 기능 권한 정책

**Version**: 1.0.0
**Last Updated**: 2025-11-03
**Owner**: Product & Pricing Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This document defines **pricing plans**, **feature entitlements**, and **quotas** for DecisionOS platform. It governs:
- **What features** each plan includes (entitlements)
- **How much usage** is allowed (quotas)
- **How much it costs** (rate cards)
- **How to enforce** limits (API gating, soft/hard limits)
- **How to upgrade/downgrade** (plan transitions)

**Scope**: All DecisionOS services (Catalog, Decisions, HITL, Guardrails, Billing, etc.)

---

### 1.2 Key Concepts

| Term | Definition | Example |
|------|------------|---------|
| **Plan (요금제)** | Pricing tier with bundled features and quotas | Free, Pro, Enterprise |
| **Entitlement (기능 권한)** | Permission to use a specific feature | `decisions.run`, `guardrails.v2` |
| **Quota (할당량)** | Maximum allowed usage within a period | 5,000 decisions/day, 200 GB storage |
| **Rate Card (요금표)** | Price per unit of usage (for overages) | ₩2 per decision call, ₩80 per GB/month |
| **Soft Limit** | Warning threshold (can exceed, but billed extra) | 80% of quota triggers warning email |
| **Hard Limit** | Absolute cap (API rejects requests beyond this) | 10,000 API calls/day (returns 429) |

---

## 2. Pricing Plans

### 2.1 Plan Tiers

| Plan | Target Audience | Base Price | Billing Cycle |
|------|----------------|------------|---------------|
| **Free** | Individual developers, hobbyists | ₩0 | N/A |
| **Pro** | Small teams, startups | ₩100,000/month | Monthly |
| **Enterprise** | Large organizations, custom needs | Negotiated | Annual contract |

---

### 2.2 Free Plan

**Base Price**: ₩0 (forever free)

**Entitlements** (read-only + limited compute):
- ✅ `catalog.read` — Browse data catalog
- ✅ `lineage.read` — View lineage graphs
- ✅ `decisions.run.basic` — Run basic decision models (no ML)
- ❌ `decisions.run.ml` — ML-based decisions (Pro+)
- ❌ `guardrails.v2` — Advanced guardrails (Pro+)
- ❌ `hitl.basic` — Human-in-the-loop review (Pro+)
- ❌ `pipelines.run` — Data pipelines (Pro+)
- ❌ `custom_models` — Upload custom models (Enterprise)

**Quotas**:
```yaml
decisions_per_day: 200        # Max 200 decision API calls per day
storage_gb: 5                 # Max 5 GB data storage
connectors: 2                 # Max 2 data source connectors
api_requests_per_min: 10      # Rate limit: 10 API calls/min
users: 1                      # Single user only (no team)
projects: 1                   # Max 1 project
```

**Rate Card** (overage charges):
- **Not applicable** (no overage allowed, API rejects requests beyond quota)

**Support**:
- 📧 Email support (48-hour response SLA)
- 📚 Community forum
- ❌ No phone/chat support

---

### 2.3 Pro Plan

**Base Price**: ₩100,000/month (billed monthly)

**Entitlements** (full platform access):
- ✅ `catalog.*` — Full catalog management (read + write)
- ✅ `lineage.*` — Lineage tracking + impact analysis
- ✅ `decisions.run` — ML-based decision models
- ✅ `pipelines.run` — Data pipeline orchestration
- ✅ `guardrails.v2` — Advanced guardrails (PII detection, policy enforcement)
- ✅ `hitl.basic` — Human-in-the-loop review queue
- ✅ `api_access` — Full REST API access
- ❌ `custom_models` — Upload custom models (Enterprise only)
- ❌ `sla_guaranteed` — SLA guarantees (Enterprise only)
- ❌ `dedicated_support` — Dedicated support engineer (Enterprise only)

**Quotas** (included in base price):
```yaml
decisions_per_day: 5000       # Max 5,000 decision calls/day (included)
storage_gb: 200               # Max 200 GB storage (included)
connectors: 10                # Max 10 data connectors
api_requests_per_min: 100     # Rate limit: 100 API calls/min
users: 10                     # Max 10 team members
projects: 10                  # Max 10 projects
hitl_cases_per_month: 500     # Max 500 HITL review cases/month
```

**Rate Card** (overage charges, billed monthly):
```yaml
decision_call: 2              # ₩2 per decision call (beyond 5,000/day)
storage_gb_month: 80          # ₩80 per GB/month (beyond 200 GB)
hitl_case: 500                # ₩500 per HITL case (beyond 500/month)
additional_user: 10000        # ₩10,000 per additional user/month
additional_project: 5000      # ₩5,000 per additional project/month
```

**Example Billing** (Pro plan, typical month):
```
Base Fee:               ₩100,000
Overage (2,000 extra decision calls × ₩2): ₩4,000
Overage (50 GB extra storage × ₩80):       ₩4,000
Total:                  ₩108,000
```

**Support**:
- 📧 Email support (4-hour response SLA, business hours)
- 💬 Chat support (business hours)
- 📞 Phone support (business hours, Korean + English)
- 📚 Detailed documentation + video tutorials

---

### 2.4 Enterprise Plan

**Base Price**: **Negotiated** (custom quote, annual contract)

**Entitlements** (everything + custom):
- ✅ **All Pro features**
- ✅ `custom_models.*` — Upload and deploy custom ML models
- ✅ `sla_guaranteed` — 99.9% uptime SLA with financial penalties
- ✅ `dedicated_support` — Dedicated support engineer (8-hour SLA)
- ✅ `audit_compliance` — SOC 2, ISO 27001 compliance reports
- ✅ `custom_integrations` — Custom API integrations, webhooks
- ✅ `on_premise` — On-premise deployment option (additional cost)
- ✅ `white_label` — White-label UI (remove DecisionOS branding)

**Quotas** (negotiated, typical):
```yaml
decisions_per_day: 200000     # 200K decisions/day (negotiable)
storage_gb: 2000              # 2 TB storage (negotiable)
connectors: 100               # 100+ connectors (unlimited in practice)
api_requests_per_min: 1000    # Rate limit: 1,000 API calls/min
users: unlimited              # Unlimited team members
projects: unlimited           # Unlimited projects
hitl_cases_per_month: 10000   # 10K HITL cases/month (negotiable)
```

**Rate Card** (custom, negotiated):
```yaml
decision_call: negotiated     # Typically ₩1~1.5 per call (volume discount)
storage_gb_month: 60          # ₩60 per GB/month (volume discount)
hitl_case: negotiated         # Typically ₩300~400 per case
```

**Support**:
- 📧 Email support (30-minute response SLA, 24/7)
- 💬 Chat support (24/7)
- 📞 Phone support (24/7, multilingual)
- 👨‍💼 Dedicated Customer Success Manager (CSM)
- 🛠️ Quarterly Business Reviews (QBRs)
- 📊 Custom training and onboarding

**Contract Terms**:
- **Minimum commitment**: 1 year (annual prepay, or monthly with 12-month contract)
- **Cancellation**: 90-day notice required
- **Renewal**: Auto-renewal unless canceled

---

## 3. Feature Entitlements

### 3.1 Entitlement Hierarchy

**Notation**: `service.action.qualifier`

**Examples**:
- `catalog.read` — Read data catalog
- `catalog.write` — Create/update catalog entries
- `catalog.*` — All catalog actions (read + write + delete)
- `decisions.run.basic` — Run basic decision models
- `decisions.run.ml` — Run ML-based decision models
- `*` — All features (Enterprise only)

---

### 3.2 Entitlement Matrix

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| **Catalog** |
| `catalog.read` | ✅ | ✅ | ✅ |
| `catalog.write` | ❌ | ✅ | ✅ |
| `catalog.delete` | ❌ | ✅ | ✅ |
| **Lineage** |
| `lineage.read` | ✅ | ✅ | ✅ |
| `lineage.write` | ❌ | ✅ | ✅ |
| `lineage.impact_analysis` | ❌ | ✅ | ✅ |
| **Decisions** |
| `decisions.run.basic` | ✅ | ✅ | ✅ |
| `decisions.run.ml` | ❌ | ✅ | ✅ |
| `decisions.run.custom` | ❌ | ❌ | ✅ |
| **Guardrails** |
| `guardrails.v1` | ❌ | ✅ | ✅ |
| `guardrails.v2` | ❌ | ✅ | ✅ |
| **HITL (Human-in-the-Loop)** |
| `hitl.basic` | ❌ | ✅ | ✅ |
| `hitl.advanced` | ❌ | ❌ | ✅ |
| **Pipelines** |
| `pipelines.run` | ❌ | ✅ | ✅ |
| `pipelines.schedule` | ❌ | ✅ | ✅ |
| **API Access** |
| `api.read` | ✅ | ✅ | ✅ |
| `api.write` | ❌ | ✅ | ✅ |
| `api.admin` | ❌ | ❌ | ✅ |
| **Custom Models** |
| `custom_models.upload` | ❌ | ❌ | ✅ |
| `custom_models.deploy` | ❌ | ❌ | ✅ |
| **SLA & Compliance** |
| `sla.99_9` | ❌ | ❌ | ✅ |
| `compliance.soc2` | ❌ | ❌ | ✅ |
| `compliance.iso27001` | ❌ | ❌ | ✅ |

---

### 3.3 Enforcement

**API Gateway Middleware**:
```python
def check_entitlement(org_id, feature):
    """Check if org has entitlement for feature."""
    org = get_org(org_id)
    plan = get_plan(org.plan_id)

    # Check if feature is in plan's entitlements
    if feature in plan.entitlements:
        return True

    # Check for wildcard (e.g., "catalog.*" matches "catalog.read")
    for entitlement in plan.entitlements:
        if entitlement.endswith('.*') and feature.startswith(entitlement[:-2]):
            return True

    # Enterprise has "*" (all features)
    if '*' in plan.entitlements:
        return True

    return False

# Usage in API handler
@app.post("/api/v1/decisions/run")
def run_decision(org_id, model_type):
    feature = f"decisions.run.{model_type}"  # e.g., "decisions.run.ml"

    if not check_entitlement(org_id, feature):
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{feature}' not available on your plan. Upgrade to Pro or Enterprise."
        )

    # Proceed with decision execution
    ...
```

**Error Response**:
```json
{
  "error": "ENTITLEMENT_DENIED",
  "message": "Feature 'decisions.run.ml' not available on Free plan.",
  "current_plan": "free",
  "required_plan": "pro",
  "upgrade_link": "https://portal.decisionos.com/billing/upgrade"
}
```

---

## 4. Quotas & Rate Limits

### 4.1 Quota Types

**Time-Based**:
- `per_day` — Resets daily at 00:00 UTC
- `per_month` — Resets monthly on 1st day at 00:00 UTC
- `per_min` — Sliding window (last 60 seconds)

**Cumulative**:
- `total` — Lifetime quota (e.g., storage, users)

---

### 4.2 Quota Enforcement

**Soft Limit** (warning, allow overage with charges):
```yaml
quota:
  decisions_per_day:
    included: 5000            # Pro plan base
    soft_limit: 4000          # Warn at 80%
    hard_limit: 10000         # Absolute max (reject beyond this)
    overage_rate: 2           # ₩2 per call beyond 5,000
```

**Behavior**:
- **0 - 4,000 calls**: Normal operation
- **4,000 - 5,000 calls**: Email warning: "You've used 80% of daily quota. Consider upgrading."
- **5,000 - 10,000 calls**: Allowed, billed at ₩2/call
- **>10,000 calls**: API returns `429 Too Many Requests`

**Hard Limit** (strict cap, no overage):
```yaml
quota:
  api_requests_per_min:
    limit: 100                # Pro plan
    hard_limit: true          # No overage allowed
```

**Behavior**:
- **0 - 100 calls/min**: Normal
- **>100 calls/min**: API returns `429 Too Many Requests` immediately (no billing)

---

### 4.3 Quota Tracking

**Implementation**:
```python
from datetime import datetime, timedelta, UTC
import redis

redis_client = redis.Redis()

def check_quota(org_id, metric, plan_quota):
    """Check if org is within quota for metric."""

    # Get current usage (sliding window for per_day)
    key = f"quota:{org_id}:{metric}:{datetime.now(UTC).date()}"
    current_usage = int(redis_client.get(key) or 0)

    # Check against quota
    if current_usage >= plan_quota.hard_limit:
        raise QuotaExceededError(
            metric=metric,
            current=current_usage,
            limit=plan_quota.hard_limit
        )

    # Warn if approaching soft limit
    if current_usage >= plan_quota.soft_limit and current_usage < plan_quota.soft_limit + 10:
        send_quota_warning_email(org_id, metric, current_usage, plan_quota)

    # Increment usage
    redis_client.incr(key)
    redis_client.expire(key, timedelta(days=2))  # Keep for 2 days (grace period)

    return {
        "allowed": True,
        "current_usage": current_usage + 1,
        "quota_limit": plan_quota.hard_limit,
        "overage_charges": max(0, current_usage - plan_quota.included) * plan_quota.overage_rate
    }
```

**Error Response**:
```json
{
  "error": "QUOTA_EXCEEDED",
  "message": "Daily decision call quota exceeded (10,000 / 10,000).",
  "metric": "decisions_per_day",
  "current_usage": 10000,
  "quota_limit": 10000,
  "reset_at": "2025-11-04T00:00:00Z",
  "upgrade_link": "https://portal.decisionos.com/billing/upgrade"
}
```

---

## 5. Plan Transitions

### 5.1 Upgrade

**Free → Pro**:
```
User clicks "Upgrade to Pro" in portal
→ Redirect to payment page
→ Enter credit card
→ Charge ₩100,000 (prorated for remaining month)
→ Plan immediately upgraded (entitlements + quotas updated)
→ Email confirmation
```

**Proration** (if upgrading mid-month):
```
Upgrade on Nov 15 (15 days remaining in month)
Pro monthly price: ₩100,000
Prorated charge: ₩100,000 × (15 / 30) = ₩50,000
Next billing: Dec 1 (full ₩100,000)
```

**Pro → Enterprise**:
```
User contacts sales team
→ Custom quote prepared (based on forecasted usage)
→ Contract negotiation (1-year commitment)
→ Sign contract
→ Plan upgraded manually by admin
→ CSM assigned
```

---

### 5.2 Downgrade

**Pro → Free**:
```
User clicks "Downgrade to Free" in portal
→ Warning: "You will lose access to Pro features. Confirm?"
→ User confirms
→ Plan downgraded at end of current billing cycle (not immediately)
→ Unused portion of current month: No refund (used as service credit)
→ Email confirmation
```

**Data Retention** (after downgrade):
- **Storage quota exceeded**: Data becomes read-only (cannot add new data)
- **Grace period**: 30 days to export or delete data to fit Free quota (5 GB)
- **After 30 days**: Oldest data automatically archived (downloadable via support request)

**Enterprise → Pro**:
```
User contacts support (cannot self-serve)
→ Contract review (check for early termination fees)
→ Downgrade scheduled for contract end date
→ CSM offboarded, support SLA downgraded
```

---

### 5.3 Cancellation

**Cancel Subscription** (Pro plan):
```
User clicks "Cancel Subscription" in portal
→ Warning: "Your plan will remain active until <end of billing cycle>."
→ User confirms
→ Subscription canceled (no further charges)
→ Plan downgrades to Free at end of cycle
→ Email confirmation
```

**Data Export** (before cancellation):
- User receives email: "Your subscription ends on <date>. Export your data before then."
- Self-service export available in portal (download all projects as ZIP)

**Refunds**:
- **No refunds** for unused portion of month (Pro plan, ToS)
- **Enterprise**: Per contract terms (typically prorated refund if early termination)

---

## 6. Billing & Invoicing

### 6.1 Billing Cycle

**Monthly** (Pro plan):
- **Billing Date**: 1st of every month (for previous month's usage)
- **Payment Due**: 3 days after invoice issued (auto-charged to card on file)
- **Grace Period**: 7 days (service continues, but warnings sent)
- **Suspension**: Day 8 if payment fails (service suspended, data retained for 30 days)

**Annual** (Enterprise):
- **Billing Date**: Contract anniversary date
- **Payment Terms**: Net 30 (invoice sent, payment due within 30 days)
- **Grace Period**: 15 days
- **Suspension**: Day 46 if payment fails

---

### 6.2 Invoice Line Items

**Example Invoice** (Pro plan, November 2025):
```
════════════════════════════════════════════════════════════
INVOICE #INV-2025-11-00123
Billing Period: 2025-11-01 ~ 2025-11-30
════════════════════════════════════════════════════════════

Org: TestCorp (org_abc123)
Plan: Pro
Billing Email: billing@testcorp.com

LINE ITEMS:
────────────────────────────────────────────────────────────
Description                        Qty      Unit Price   Amount
────────────────────────────────────────────────────────────
Pro Plan (Monthly Base Fee)        1        ₩100,000    ₩100,000

Usage Overages:
  Decision Calls (overage)       2,000      ₩2          ₩4,000
    (Base: 5,000/day included, Used: 7,000/day avg)

  Storage (overage)                 50 GB   ₩80         ₩4,000
    (Base: 200 GB included, Used: 250 GB)

  HITL Cases (overage)             100      ₩500        ₩50,000
    (Base: 500/month included, Used: 600)

────────────────────────────────────────────────────────────
Subtotal:                                               ₩158,000
VAT (10%):                                              ₩15,800
────────────────────────────────────────────────────────────
TOTAL:                                                  ₩173,800
════════════════════════════════════════════════════════════

Payment Method: Visa **** 1234
Payment Status: PAID (2025-12-03)

Questions? billing@decisionos.com | 1588-XXXX
════════════════════════════════════════════════════════════
```

---

## 7. Versioning & Changes

### 7.1 Plan Changes

**Notification Period**:
- **Price increases**: 30 days advance notice (email to all affected orgs)
- **Feature additions**: Immediate (no notice required, always additive)
- **Feature removals**: 90 days advance notice + migration path

**Grandfather Clause**:
- Existing customers on old plans can remain (unless plan deprecated)
- Example: "Legacy Pro" plan (₩80,000/month) → New "Pro Plus" (₩100,000/month)
  - Existing Legacy Pro customers: Can keep old plan OR upgrade to new plan
  - New customers: Only new plan available

---

### 7.2 Rate Card Changes

**Policy**:
- Rate cards can change with **30 days notice**
- Changes apply to **new usage** only (not retroactive)
- Customers can lock in current rates with **annual contract** (Enterprise)

**Example**:
```
Notification (Nov 1):
  "Effective Dec 1, 2025, decision call overage rate increases from ₩2 → ₩2.5"

Billing (Dec 1 invoice):
  Nov 1-30 usage: Billed at old rate (₩2)
  Dec 1+ usage: Billed at new rate (₩2.5)
```

---

## 8. Related Documents

- [Billing Terms (Korean)](billing_terms_ko.md) — Customer-facing billing policy
- [Invoice Templates](../templates/invoice_pdf.md) — Invoice PDF/JSON structure
- [Cost Guard Runbook](../ops/runbook_cost_guard.md) — Margin monitoring and optimization
- [Payments Policy](payments_policy_ko.md) — Payment methods, refunds, disputes

---

## 9. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-03 | Product & Pricing Team | Gate-S: Initial plans & entitlements policy (Free, Pro, Enterprise) |

---

**END OF DOCUMENT**
