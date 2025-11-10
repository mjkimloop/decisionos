# Error Budget Policy — Release Gating & Exception Management

**Version**: 2.0.0
**Last Updated**: 2025-11-04
**Owner**: SRE + Release Engineering
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

**Error budgets** quantify how much failure is acceptable before reliability work must take precedence over feature development. This policy governs:

1. **Deployment gating** (auto-block releases when budget exhausted)
2. **Exception approval** (override process for critical fixes)
3. **Accountability** (tie budgets to team incentives/planning)

**Key Principle**: *Reliability is a feature.* Error budgets balance innovation speed with user experience.

---

### 1.2 Definitions

| Term | Definition | Example |
|------|------------|---------|
| **SLO** (Service Level Objective) | Target for a service's reliability | `availability ≥ 99.9%` over 30 days |
| **Error Budget** | Allowed failure = `1 - SLO` | `0.1%` downtime = 43.2 min/month |
| **Burn Rate** | Rate of budget consumption relative to target | `2.0` = burning 2x faster than sustainable |
| **Gating Status** | CI/CD decision based on remaining budget | `allow` / `review` / `block` |
| **Override** | Manual approval to bypass gate | Requires oncall + duty manager sign-off |

---

## 2. Error Budget Calculation

### 2.1 Formula

**For Availability SLOs**:
```
SLO Target:           99.9% (example)
Error Budget:         1 - 0.999 = 0.001 (0.1%)
Allowed Downtime/30d: 30 days × 24h × 60min × 0.001 = 43.2 minutes

Consumed Budget:
  Actual Availability = 99.85% (from metrics)
  Actual Error Rate   = 1 - 0.9985 = 0.0015 (0.15%)
  Consumed            = 0.0015 / 0.001 = 150% (budget exhausted!)

Remaining Budget:
  Remaining = 1 - (Consumed / Total)
            = 1 - 1.5 = -50% (over budget)
```

**For Latency SLOs** (percentile-based):
```
SLO Target:       p95 ≤ 500ms
Measurement:      % of time p95 exceeds 500ms over 30d window
Error Budget:     Allow p95 > 500ms for ≤ 0.1% of the time (43.2 min/month)
```

---

### 2.2 Burn Rate

**Definition**: How fast you're consuming your error budget relative to the target rate.

```
Burn Rate = (Actual Error Rate over Window) / (SLO Error Rate)

Example:
  SLO = 99.9% → SLO Error Rate = 0.1%

  1-hour window:
    Actual Availability = 99.7%
    Actual Error Rate   = 0.3%
    Burn Rate           = 0.3% / 0.1% = 3.0

  Interpretation: At this rate, 30-day budget exhausted in 10 days.
```

**Multi-Window Strategy** (reduce alert noise):

| Window | Burn Rate Threshold | Severity | Action | Rationale |
|--------|---------------------|----------|--------|-----------|
| **5 min** | > 10.0 | P0 | Immediate rollback | Catastrophic failure (e.g., 50% error rate) |
| **1 hour** | > 2.0 | P1 | Page oncall, investigate | Severe issue likely to exhaust budget |
| **6 hour** | > 1.0 | P2 | Alert + review | Sustained issue, still time to fix |

**Rationale**:
- 5-min window catches immediate disasters (deploy went bad)
- 6-hour window catches slow burns (gradual degradation)
- Avoids paging for transient spikes (1 bad minute won't trigger 6h alert)

---

## 3. Deployment Gating

### 3.1 Gate Decision Matrix

**Remaining Error Budget** (30-day rolling window) determines gate status:

| Remaining Budget | Status | Gate Decision | Required Approvals | Deploy Allowed? |
|------------------|--------|---------------|-------------------|-----------------|
| **> 20%** | 🟢 GREEN | `allow` | None (auto-approve) | ✅ Yes |
| **10% – 20%** | 🟡 YELLOW | `review` | Oncall engineer | ⚠️ With approval |
| **< 10%** | 🔴 RED | `block` | Oncall + Duty Manager | ❌ No (except P0 fixes) |

**Additional Rules**:
- **P0 fixes** (security CVEs, data-loss bugs): Always allowed, but require override approval
- **Canary rollbacks**: Bypass gate (safety mechanism, not new code)
- **Infrastructure-only changes** (K8s config, no app code): Bypass gate (lower risk)

---

### 3.2 API Endpoint

**GET** `/api/v1/obs/errorbudget/status?service={service_name}`

**Response**:
```json
{
  "service": "decision-api",
  "window": "30d",
  "slo_target": 0.999,
  "actual_availability": 0.9985,
  "error_budget_total": 0.001,
  "error_budget_consumed": 0.0005,
  "error_budget_remaining": 0.0005,
  "remaining_pct": 50.0,
  "status": "allow",
  "burn_rate_1h": 0.8,
  "burn_rate_6h": 1.2,
  "gate_decision": "allow",
  "last_updated": "2025-11-04T14:23:00Z"
}
```

**Status Codes**:
- `200 OK` — Gate status returned
- `503 Service Unavailable` — Observability pipeline down → **fail-open** (allow deploy, alert SRE)

---

### 3.3 CI/CD Integration

**GitHub Actions Example**:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  check-error-budget:
    runs-on: ubuntu-latest
    steps:
      - name: Query Error Budget
        id: eb
        run: |
          RESPONSE=$(curl -sf https://obs.decisionos.internal/api/v1/obs/errorbudget/status?service=decision-api)
          STATUS=$(echo $RESPONSE | jq -r '.status')
          REMAINING=$(echo $RESPONSE | jq -r '.remaining_pct')

          echo "status=$STATUS" >> $GITHUB_OUTPUT
          echo "remaining=$REMAINING" >> $GITHUB_OUTPUT

      - name: Gate Decision
        run: |
          if [[ "${{ steps.eb.outputs.status }}" == "block" ]]; then
            echo "❌ Error budget exhausted (${{ steps.eb.outputs.remaining }}% remaining)."
            echo "Deploy blocked. See runbook: https://wiki/oncall/error-budget-exhausted"
            exit 1
          elif [[ "${{ steps.eb.outputs.status }}" == "review" ]]; then
            echo "⚠️  Error budget low (${{ steps.eb.outputs.remaining }}% remaining)."
            echo "Oncall approval required. Posting to Slack..."
            # Post to Slack, wait for approval (manual gate)
          else
            echo "✅ Error budget healthy (${{ steps.eb.outputs.remaining }}% remaining). Proceeding."
          fi

  deploy:
    needs: check-error-budget
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        run: |
          kubectl set image deployment/decision-api api=${{ github.sha }}
```

---

### 3.4 Fail-Open Policy

**Problem**: What if the observability pipeline itself is down?

**Policy**: **Fail-open** (allow deploys) to avoid blocking engineers due to tooling issues.

**Implementation**:
```bash
# If /errorbudget/status returns 5xx or times out:
if ! curl -sf --max-time 5 https://obs.../errorbudget/status; then
  echo "⚠️  Observability API unavailable. Failing open (allowing deploy)."
  # Alert SRE to fix obs pipeline
  curl -X POST https://slack.../webhook -d '{"text":"Error budget API down, deploys failing open"}'
fi
```

---

## 4. Exception & Override Process

### 4.1 Scenarios Requiring Override

| Scenario | Justification | Approval Required |
|----------|--------------|-------------------|
| **P0 Security Fix** (CVE) | User data at risk, regulatory requirement | Oncall + Duty Manager |
| **Data Loss Bug** | Silent corruption affecting prod DB | Oncall + Duty Manager |
| **Compliance Deadline** | Regulatory deadline (e.g., GDPR audit due) | Oncall + Compliance Officer |
| **Revenue-Critical Hotfix** | Payment processor down, losing $X/min | Oncall + Finance Director |

**Not Valid**:
- "We promised the feature to a customer" → Deploy to staging, wait for budget recovery
- "It's just a small change" → Small changes cause big outages; no exception

---

### 4.2 Approval Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Engineer files override request                          │
│    dosctl obs eb override --service X --reason "..."        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Oncall Engineer reviews (SLA: 30 min)                    │
│    - Validates severity, checks recent incidents            │
│    - Approves or denies via Slack bot                       │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Duty Manager (or Director) reviews (SLA: 1 hour)         │
│    - Second approval required for all overrides             │
│    - Can add conditions (e.g., "canary only, 10% traffic")  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Override granted (time-limited, default 2h)              │
│    - CI/CD gate bypassed for specified duration             │
│    - Audit log entry created                                │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Post-mortem required (within 48h)                        │
│    - Why was error budget exhausted?                        │
│    - Why was override necessary?                            │
│    - What reliability work is needed?                       │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.3 CLI Command

**File Override Request**:
```bash
dosctl obs eb override \
  --service decision-api \
  --reason "P0: CVE-2025-9999 RCE in jackson-databind, patch available" \
  --severity p0 \
  --duration 2h \
  --link https://nvd.nist.gov/vuln/detail/CVE-2025-9999
```

**Output**:
```
Override request submitted (ID: OVR-2025-1104-001)
Status: pending_oncall_approval
Oncall notified: @alice (Slack)
SLA: Approval within 30 min

Track status: dosctl obs eb override status OVR-2025-1104-001
```

**Approval** (by oncall engineer):
```bash
# Via Slack bot:
/approve-override OVR-2025-1104-001 reason="Valid CVE, patch tested in staging"

# Or via CLI:
dosctl obs eb override approve OVR-2025-1104-001 \
  --approver oncall:alice@company.com \
  --comment "Approved, CVE is critical. Requesting manager approval."
```

**Manager Approval**:
```bash
dosctl obs eb override approve OVR-2025-1104-001 \
  --approver manager:bob@company.com \
  --condition "canary_only,max_traffic=10%,duration=1h"
```

**Result**:
```
Override APPROVED (ID: OVR-2025-1104-001)
Valid until: 2025-11-04 16:23:00 UTC (2h from now)
Conditions: canary_only, max_traffic=10%, duration=1h
Approvers: alice@company.com (oncall), bob@company.com (duty_manager)

CI/CD gate bypassed for decision-api.
Proceed with deployment.
```

---

### 4.4 Audit Trail

**All overrides logged**:
```sql
SELECT
  override_id,
  service,
  requested_by,
  requested_at,
  reason,
  severity,
  oncall_approver,
  manager_approver,
  granted_at,
  expires_at,
  conditions,
  postmortem_link
FROM audit_error_budget_overrides
WHERE service = 'decision-api'
ORDER BY requested_at DESC
LIMIT 10;
```

**Monthly Review**:
- SRE presents override report to Eng leadership
- High override frequency → SLO may be too strict, or systemic reliability issues
- Pattern: "All overrides are security CVEs" → Need faster patch pipeline

---

## 5. Budget Recovery & Remediation

### 5.1 When Budget is Exhausted

**Immediate Actions** (if `status = block`):
1. **Halt feature development**: Eng team focuses 100% on reliability
2. **Root cause analysis**: Why did we exceed SLO? (Traffic spike, bad deploy, dependency failure?)
3. **Remediation backlog**: File bugs, prioritize fixes
4. **Communicate**: Update stakeholders (PM, customers if applicable)

**Deployment Freeze Exceptions**:
- **P0 fixes only**: Security, data loss, compliance
- **Rollbacks**: Always allowed (restore known-good state)
- **Infrastructure hardening**: Allowed if it directly improves SLO (e.g., add capacity, fix known issue)

---

### 5.2 Budget Recovery Timeline

**Rolling Window** (30 days):
- Budget recovers as old failures "age out" of the window
- Example: Large outage on Day 1 (consumed 80% of budget) → By Day 31, that outage no longer counts

**Accelerated Recovery** (optional):
- **Pro-active SLO buffer**: If running at 99.95% actual vs. 99.9% target, you're "banking" buffer for future issues
- **Trade-off**: Tighter SLO (99.95%) → smaller budget, but faster recovery if you achieve it

**Typical Recovery** (after major incident):
```
Day 0:  Incident (4h outage) → Budget exhausted (status: block)
Day 1:  Postmortem, file remediation bugs
Day 7:  50% of budget recovered (incident now represents only half of 30d window)
Day 14: 75% recovered
Day 30: 100% recovered (incident fully aged out)
```

---

### 5.3 Remediation Prioritization

**SRE + PM Collaboration**:
1. **Critical**: Fixes that directly restore SLO (e.g., auto-scaling, failover logic)
2. **High**: Reduce blast radius (circuit breakers, retries, graceful degradation)
3. **Medium**: Observability gaps (add alerts, dashboards for early detection)
4. **Low**: Nice-to-haves (refactoring for future velocity)

**Velocity Impact**:
- While in `block` status, sprint velocity drops (no new features)
- **Trade-off accepted**: Short-term velocity loss → long-term reliability gain

---

## 6. Burn Rate Alerts

### 6.1 Alert Definitions

**P0 — Immediate Rollback** (5-min window):
```yaml
- alert: ErrorBudgetCriticalBurn5m
  expr: |
    (
      (1 - (sum(rate(http_requests_total{status=~"2..",service="decision-api"}[5m]))
            / sum(rate(http_requests_total{service="decision-api"}[5m]))))
      / (1 - 0.999)
    ) > 10.0
  for: 2m  # Sustained for 2 min
  labels:
    severity: p0
    service: decision-api
  annotations:
    summary: "decision-api burning error budget at 10x (5m window)"
    action: |
      IMMEDIATE ROLLBACK REQUIRED
      1. dosctl deploy rollback decision-api --to-version <previous>
      2. Set canary to 0%
      3. Page oncall + duty manager
      4. Check logs: dosctl logs tail decision-api --level error
```

**P1 — Investigate** (1-hour window):
```yaml
- alert: ErrorBudgetHighBurn1h
  expr: |
    # Same burn rate formula with [1h] window
    (...) > 2.0
  for: 5m
  labels:
    severity: p1
    service: decision-api
  annotations:
    summary: "decision-api burning error budget at 2x (1h window)"
    action: |
      Investigate within 15 min:
      1. Recent deploys? dosctl deploy history decision-api
      2. Traffic spike? Check /web/obs/service/decision-api
      3. Dependency issues? Check upstream services
      Runbook: https://wiki/runbooks/high-error-rate
```

**P2 — Review** (6-hour window):
```yaml
- alert: ErrorBudgetSustainedBurn6h
  expr: |
    # Same with [6h] window
    (...) > 1.0
  for: 10m
  labels:
    severity: p2
    service: decision-api
  annotations:
    summary: "decision-api burning error budget at 1x+ (6h sustained)"
    action: |
      Schedule review within 1 hour:
      1. File incident ticket
      2. Analyze trends (gradual degradation?)
      3. Plan remediation for next sprint
```

---

### 6.2 Alert Routing

**Integration**: Prometheus → Alertmanager → Slack / PagerDuty

```yaml
# alertmanager.yml
route:
  receiver: default
  routes:
    - match:
        severity: p0
      receiver: pagerduty-critical
      continue: true
    - match:
        severity: p0
      receiver: slack-incidents
    - match:
        severity: p1
      receiver: slack-oncall
    - match:
        severity: p2
      receiver: slack-observability

receivers:
  - name: pagerduty-critical
    pagerduty_configs:
      - service_key: <PD_SERVICE_KEY>
        description: "{{ .CommonAnnotations.summary }}"
  - name: slack-oncall
    slack_configs:
      - channel: "#oncall"
        title: "{{ .CommonAnnotations.summary }}"
        text: "{{ .CommonAnnotations.action }}"
```

---

## 7. Reporting & Accountability

### 7.1 Monthly SLO Report

**Template**:
```markdown
# SLO Report — October 2025

## Executive Summary
- **Services meeting SLO**: 6 / 7 (86%)
- **Total error budget consumed**: 45% (avg across services)
- **Incidents**: 2 (1 caused by deploy, 1 by external dependency)
- **Overrides granted**: 3 (all P0 security patches)

## Service Breakdown

### decision-api
- **SLO Target**: 99.9% availability
- **Actual**: 99.85% ❌ (missed by 0.05%)
- **Error Budget**: 150% consumed (50% over budget)
- **Root Cause**: Oct 15 deploy introduced retry bug (4h degradation)
- **Remediation**: Retry logic fixed, added integration test (PROJ-1234)

### guardrails
- **SLO Target**: 99.95% availability
- **Actual**: 99.97% ✅
- **Error Budget**: 40% consumed (60% remaining)
- **Notes**: Excellent month, no incidents

[... repeat for all services ...]

## Lessons Learned
1. Need better canary monitoring (deploy issue should've been caught at 5% traffic)
2. Retry logic needs chaos testing
3. External dependency (Auth0) caused 1h outage → Add circuit breaker

## Action Items
- [ ] Implement enhanced canary metrics (ENG-5678)
- [ ] Add Auth0 circuit breaker (ENG-5679)
- [ ] Schedule chaos gameday for retry paths (ENG-5680)
```

---

### 7.2 Team Incentives (Optional)

**Approach**: Tie error budgets to team goals (not individual performance reviews).

**Example OKR**:
```
Team OKR (Q4 2025):
  Objective: Improve decision-api reliability
  Key Results:
    1. Meet 99.9% SLO for 3 consecutive months ✅
    2. Reduce P0 incidents from 5/quarter → 2/quarter ✅
    3. Deploy frequency: ≥ 10/week (velocity) ⚠️ (8/week achieved)
```

**Avoid**: Punishing teams for missing SLO during legitimate incidents (undermines blameless culture).

---

## 8. Related Policies

| Policy | Purpose | Link |
|--------|---------|------|
| **SLI/SLO Catalog** | Define SLOs for all services | [sli_slo_catalog.md](sli_slo_catalog.md) |
| **Incident Response** | P0/P1 runbooks, postmortem process | [ops/runbook_oncall.md](ops/runbook_oncall.md) |
| **Deployment Policy** | Canary strategy, rollback procedures | [ops/runbook_deployment.md](ops/runbook_deployment.md) |
| **Observability Architecture** | OTel, metrics/logs/traces | [docs/observability_arch.md](docs/observability_arch.md) |

---

## 9. FAQ

**Q: What if we're consistently exceeding our SLO (e.g., 99.95% actual vs. 99.9% target)?**
A: Two options:
1. **Tighten SLO** to 99.95% (invest error budget in features, increase velocity)
2. **Keep SLO, bank buffer** (headroom for future incidents/experiments)

Recommendation: Review quarterly. If exceeding by >1% for 90 days, consider tightening.

---

**Q: What if the SLO is too strict (we always miss it)?**
A:
1. **Short-term**: File overrides as needed, but this is unsustainable
2. **Medium-term**: Remediation sprints (focus on reliability)
3. **Long-term**: If systemic (e.g., legacy architecture), propose SLO relaxation via RFC (requires VP Eng approval)

**Red flag**: If >50% of deploys require overrides, SLO is misaligned with reality.

---

**Q: Can we have different SLOs for different endpoints?**
A: Yes, but adds complexity:
- **Option 1**: Composite SLO (weighted by traffic): `SLO = 0.8×SLO_critical + 0.2×SLO_non_critical`
- **Option 2**: Separate services (microservices pattern)

Most teams start with single SLO per service, refine later.

---

**Q: What if a dependency (external API) causes us to miss our SLO?**
A:
1. **SLO includes dependencies** (user doesn't care whose fault it is)
2. **Mitigation**: Circuit breakers, retries, fallback logic
3. **Escalation**: If chronic, negotiate SLA with vendor or switch providers

**Example**: Auth0 causes 1h outage → counts against our error budget → We add circuit breaker to fail fast, preserve budget.

---

**Q: How do we handle planned maintenance?**
A: **Two approaches**:
1. **Exclude from SLO** (maintenance windows don't count) — Common for enterprise B2B
2. **Include in SLO** (forces zero-downtime deploys) — Common for consumer-facing

DecisionOS policy: **Include** (motivates rolling deploys, blue/green, canaries).

---

## 10. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2025-11-04 | SRE + Release Eng | Gate-T: Add multi-window burn rate, CI/CD gating, override CLI |
| 1.1.0 | 2025-08-20 | SRE Team | Add exception approval flow, audit trail |
| 1.0.0 | 2025-06-01 | SRE Team | Initial error budget policy (manual enforcement) |

---

**END OF DOCUMENT**
