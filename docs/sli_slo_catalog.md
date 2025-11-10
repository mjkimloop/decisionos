# SLI/SLO Catalog — Observability v2

**Version**: 2.0.0
**Last Updated**: 2025-11-04
**Owner**: Platform Observability Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This catalog defines **Service Level Indicators (SLIs)** and **Service Level Objectives (SLOs)** for all DecisionOS services. SLIs measure service health; SLOs set reliability targets. Together with error budgets, they drive:

- **Release gating** (prevent deploys during budget exhaustion)
- **Prioritization** (reliability work vs. features)
- **Accountability** (objective service-quality contracts)

### 1.2 SLI/SLO Framework

```
┌─────────────────────────────────────────────────────────────┐
│ SLI (Service Level Indicator)                              │
│  → Quantitative measure of service behavior                │
│     Example: success_rate = 2xx_responses / total_requests │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ SLO (Service Level Objective)                              │
│  → Target value for an SLI over a window                   │
│     Example: success_rate ≥ 99.9% (30d rolling)            │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Error Budget = 1 - SLO                                      │
│  → Allowed failure during window                           │
│     Example: 0.1% over 30d = 43.2 minutes downtime/month   │
└─────────────────────────────────────────────────────────────┘
```

**Principles**:
1. **User-centric**: SLIs reflect end-user experience (latency, availability, correctness)
2. **Actionable**: Breach → clear runbook escalation
3. **Achievable**: Target set based on historical p50 performance + headroom
4. **Balanced**: Not 100% (allow innovation), not too low (user churn)

---

## 2. Service Catalog

### 2.1 API Gateway / Decision API

**Service**: `decision-api`
**Criticality**: P0 (user-facing, real-time lending decisions)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **Availability** | `count(status=2xx) / count(all)` | ≥ 99.9% | 30d rolling | `rate(http_requests_total{status=~"2.."}[30d]) / rate(http_requests_total[30d])` |
| **Latency p95** | 95th percentile response time | ≤ 500ms | 30d rolling | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[30d]))` |
| **Latency p99** | 99th percentile response time | ≤ 800ms | 30d rolling | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[30d]))` |
| **Throughput** | Requests per second | ≥ 200 rps | 5m | `rate(http_requests_total[5m])` |

**Error Budget** (30d):
- Availability: 0.1% → **43.2 minutes** downtime allowed
- Latency: 0.1% → **43.2 minutes** of slow responses (>500ms at p95)

**Burn Rate Alerts**:
```yaml
- alert: DecisionAPIHighBurnRate1h
  expr: |
    (1 - (
      sum(rate(http_requests_total{service="decision-api",status=~"2.."}[1h]))
      /
      sum(rate(http_requests_total{service="decision-api"}[1h]))
    )) / (1 - 0.999) > 2.0
  for: 5m
  annotations:
    summary: "decision-api burning error budget at 2x rate (1h window)"
    action: "Review recent deploys, check logs for 5xx spike"
```

---

### 2.2 Data Pipeline / ETL

**Service**: `etl-pipeline`
**Criticality**: P1 (batch, but impacts daily underwriting models)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **Freshness** | `now() - max(event_timestamp)` | ≤ 15 min | 1h rolling | `time() - max(kafka_consumer_lag_seconds{job="etl"})` |
| **Success Rate** | `count(success) / count(runs)` | ≥ 99.5% | 30d rolling | `rate(pipeline_runs_total{status="success"}[30d]) / rate(pipeline_runs_total[30d])` |
| **Reprocess Rate** | `count(retries) / count(runs)` | ≤ 2% | 7d rolling | `rate(pipeline_runs_total{retry="true"}[7d]) / rate(pipeline_runs_total[7d])` |

**Error Budget** (30d):
- Success rate: 0.5% → ~216 minutes of failed runs
- Freshness: measured at p95, alert if lag > 30min for 3 consecutive checks

---

### 2.3 Catalog & Search

**Service**: `catalog-search`
**Criticality**: P2 (internal tool, but productivity-critical)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **Availability** | `count(status=2xx) / count(all)` | ≥ 99.5% | 30d rolling | `rate(http_requests_total{service="catalog-search",status=~"2.."}[30d]) / rate(http_requests_total{service="catalog-search"}[30d])` |
| **Search Quality (P@10)** | Precision at rank 10 (from labeled eval set) | ≥ 0.80 | weekly batch eval | Offline eval job: `search_quality_precision_at_10` |
| **Latency p95** | 95th percentile search response | ≤ 300ms | 30d rolling | `histogram_quantile(0.95, rate(search_duration_seconds_bucket[30d]))` |

---

### 2.4 Guardrails v2

**Service**: `guardrails`
**Criticality**: P0 (safety/compliance layer)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **Availability** | `count(status=2xx) / count(all)` | ≥ 99.95% | 30d rolling | `rate(http_requests_total{service="guardrails",status=~"2.."}[30d]) / rate(http_requests_total{service="guardrails"}[30d])` |
| **Block Rate** | `count(blocked) / count(all)` | ≤ 0.5% (baseline) | 1d rolling | `rate(guardrails_blocked_total[1d]) / rate(guardrails_requests_total[1d])` |
| **False Positive Rate** | Manual labeling: `FP / (FP + TP)` | ≤ 2% | weekly eval | Offline eval: `guardrails_fp_rate` |
| **Overhead p95** | Added latency vs. baseline | ≤ 50ms | 30d rolling | `histogram_quantile(0.95, rate(guardrails_overhead_seconds_bucket[30d]))` |

**Notes**:
- Block rate SLO is a "quality" target, not uptime. Sudden 10x spike → incident.
- FP rate measured weekly via random sample (n=200) labeled by ops team.

---

### 2.5 Explain & Audit

**Service**: `explain-audit`
**Criticality**: P1 (regulatory requirement, but async)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **Reproducibility** | `count(explain_success) / count(explain_requests)` | ≥ 99.9% | 30d rolling | `rate(explain_success_total[30d]) / rate(explain_requests_total[30d])` |
| **Audit Completeness** | `count(audit_records) / count(decisions)` | = 100% | 1d rolling | `rate(audit_records_total[1d]) / rate(decisions_total[1d])` |
| **Latency p95** | Time to generate explanation | ≤ 2s | 30d rolling | `histogram_quantile(0.95, rate(explain_duration_seconds_bucket[30d]))` |

**Critical Invariant**:
- **Audit Completeness = 100%** is a *hard requirement* (no error budget). Any missing audit record → P0 incident.

---

### 2.6 HITL / Human Review Queue

**Service**: `hitl-queue`
**Criticality**: P1 (operations, but SLA-bound)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **First Pick Time p95** | Time from case creation to first reviewer assignment | ≤ 4h (P1 cases) | 7d rolling | `histogram_quantile(0.95, rate(hitl_first_pick_seconds_bucket{priority="p1"}[7d]))` |
| **Resolution Time p95** | Time from creation to closure | ≤ 24h (P1 cases) | 7d rolling | `histogram_quantile(0.95, rate(hitl_resolution_seconds_bucket{priority="p1"}[7d]))` |
| **Reopen Rate** | `count(reopened) / count(closed)` | ≤ 5% | 30d rolling | `rate(hitl_cases_total{status="reopened"}[30d]) / rate(hitl_cases_total{status="closed"}[30d])` |

**SLA Mapping**:
- P0 cases: First pick ≤ 1h, Resolution ≤ 4h (measured at p95)
- P1 cases: First pick ≤ 4h, Resolution ≤ 24h
- See [sla_policies.md](sla_policies.md) for full definitions.

---

### 2.7 Billing & Metering

**Service**: `billing-metering`
**Criticality**: P1 (revenue-critical, but daily batch)

| SLI Name | Definition | Target (SLO) | Window | Measurement Query |
|----------|-----------|--------------|--------|-------------------|
| **Aggregation Lag p95** | Time from event to aggregated billing record | ≤ 30 min | 1d rolling | `histogram_quantile(0.95, rate(billing_aggregation_lag_seconds_bucket[1d]))` |
| **Reconciliation Error** | `abs(actual - expected) / expected` | ≤ 0.01% (10 bps) | monthly reconciliation | Manual reconciliation report |
| **Availability** | Billing API uptime | ≥ 99.5% | 30d rolling | `rate(http_requests_total{service="billing",status=~"2.."}[30d]) / rate(http_requests_total{service="billing"}[30d])` |

---

## 3. SLO Governance

### 3.1 SLO Lifecycle

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Propose    │ -->  │   Review     │ -->  │   Approve    │
│ (Eng + PM)   │      │ (SRE + Biz)  │      │ (Dir Eng)    │
└──────────────┘      └──────────────┘      └──────────────┘
                                 ↓
                        ┌──────────────────┐
                        │  Implement       │
                        │  (Dashboards,    │
                        │   Alerts, Gates) │
                        └──────────────────┘
                                 ↓
                        ┌──────────────────┐
                        │  Monitor &       │
                        │  Iterate (90d)   │
                        └──────────────────┘
```

**Review Cadence**:
- **Quarterly**: All SLOs reviewed for achievability (if actual > target + 1%, consider tightening)
- **Ad-hoc**: On major architecture changes (e.g., Guardrails v2 → new latency profile)

**Change Process**:
1. **Propose**: RFC doc with rationale, historical data (90d), impact analysis
2. **Review**: SRE + service owner + stakeholders (1 week comment period)
3. **Approve**: Director of Engineering sign-off
4. **Implement**: Update dashboards, alert rules, error budget policies
5. **Announce**: Slack `#observability`, update this catalog

---

### 3.2 Error Budget Allocation

**Monthly Error Budget** (30d rolling window):

| Service | SLO (Availability) | Error Budget | Minutes Allowed Downtime |
|---------|-------------------|--------------|--------------------------|
| decision-api | 99.9% | 0.1% | 43.2 min |
| guardrails | 99.95% | 0.05% | 21.6 min |
| catalog-search | 99.5% | 0.5% | 216 min |
| etl-pipeline | 99.5% (success rate) | 0.5% | 216 min (in failed runs) |
| hitl-queue | 99.0% (first pick SLA met) | 1.0% | 432 min |
| billing-metering | 99.5% | 0.5% | 216 min |
| explain-audit | 99.9% (reproducibility) | 0.1% | 43.2 min |

**Burn Rate** (rate of error budget consumption):

```
burn_rate = (actual_error_rate) / (allowed_error_rate)

Examples:
- SLO = 99.9% → allowed error rate = 0.1%
- If actual error rate = 0.2% over 1h window:
  burn_rate = 0.2% / 0.1% = 2.0
  → Burning budget at 2x target rate
  → At this rate, monthly budget exhausted in 15 days
```

**Multi-Window Burn Rate Alerts**:

| Window | Burn Rate Threshold | Severity | Action |
|--------|---------------------|----------|--------|
| 5 min | > 10.0 | P0 | Immediate page, rollback canary |
| 1 hour | > 2.0 | P1 | Alert oncall, investigate |
| 6 hour | > 1.0 | P2 | Review + schedule fix |

**Rationale**: Multi-window approach reduces noise (5m spike may self-heal) while catching sustained issues (6h burn).

---

## 4. Error Budget Policy

**See**: [error_budget_policy.md](error_budget_policy.md) for full policy.

**Quick Reference**:

### 4.1 Deployment Gating

```yaml
Error Budget Status → CI/CD Gate Decision:

Remaining > 20%:       allow    (green, normal deployments)
10% ≤ Remaining ≤ 20%: review   (yellow, oncall approval required)
Remaining < 10%:       block    (red, freeze except P0 fixes)
```

**API Endpoint**:
```bash
GET /api/v1/obs/errorbudget/status?service=decision-api

Response:
{
  "service": "decision-api",
  "window": "30d",
  "slo_target": 0.999,
  "actual_availability": 0.9985,
  "error_budget_total": 0.001,
  "error_budget_consumed": 0.0005,
  "error_budget_remaining": 0.0005,
  "remaining_pct": 50.0,
  "status": "allow",        # allow | review | block
  "burn_rate_1h": 0.8,
  "burn_rate_6h": 1.2,
  "gate_decision": "allow"
}
```

**CI/CD Integration**:
```yaml
# .github/workflows/deploy.yml
- name: Check Error Budget
  run: |
    STATUS=$(curl -sf https://obs.decisonos.internal/api/v1/obs/errorbudget/status?service=decision-api | jq -r '.status')
    if [[ "$STATUS" == "block" ]]; then
      echo "❌ Error budget exhausted. Deployment blocked."
      exit 1
    elif [[ "$STATUS" == "review" ]]; then
      echo "⚠️  Error budget low. Oncall approval required."
      # Post to Slack, wait for manual approval
    fi
```

---

### 4.2 Exception Process

**Scenario**: Critical security patch needed, but error budget exhausted.

**Approval Flow**:
1. **Requestor** (engineer): File exception request via `dosctl obs eb override --service X --reason "CVE-2025-1234 RCE patch"`
2. **Oncall Engineer**: Review + approve/deny (within 30 min SLA)
3. **Duty Manager** (or Director): Second approval required (within 1h)
4. **Audit**: All overrides logged to `audit_trail` table, reviewed monthly

**Override Command**:
```bash
dosctl obs eb override \
  --service decision-api \
  --reason "P0: CVE-2025-1234 RCE exploit in commons-text, must patch immediately" \
  --duration 2h \
  --approver oncall:alice@company.com \
  --approver manager:bob@company.com
```

---

## 5. SLI Measurement Methodology

### 5.1 Data Sources

| SLI Type | Data Source | Collection Method | Retention |
|----------|-------------|-------------------|-----------|
| **HTTP Availability/Latency** | Application metrics (Prometheus) | OTel SDK `http.server.duration` histogram | 90d (raw), 2y (aggregated) |
| **Pipeline Freshness** | Kafka consumer lag + event timestamps | Custom exporter | 30d |
| **Search Quality** | Offline eval job (weekly) | Batch script → Prometheus pushgateway | 1y |
| **Guardrails FP Rate** | Manual labeling (Ops team) | Weekly sample (n=200), stored in DB | 1y |
| **HITL Timing** | Case lifecycle events (PostgreSQL) | Event-driven metrics exporter | 2y |
| **Billing Reconciliation** | Finance reconciliation report | Monthly batch, manual entry | 7y (compliance) |

---

### 5.2 Prometheus Queries (Reference)

**Availability (30d rolling)**:
```promql
# decision-api availability
sum(rate(http_requests_total{service="decision-api",status=~"2.."}[30d]))
/
sum(rate(http_requests_total{service="decision-api"}[30d]))
```

**Latency p95 (30d rolling)**:
```promql
# decision-api p95 latency
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{service="decision-api"}[30d])
)
```

**Burn Rate (1h window)**:
```promql
# decision-api burn rate (1h)
(
  1 - (
    sum(rate(http_requests_total{service="decision-api",status=~"2.."}[1h]))
    /
    sum(rate(http_requests_total{service="decision-api"}[1h]))
  )
)
/
(1 - 0.999)  # SLO target = 99.9%
```

**Freshness (ETL pipeline)**:
```promql
# ETL freshness lag (in seconds)
time() - max(kafka_consumer_last_event_timestamp{job="etl-pipeline"})
```

---

### 5.3 Sampling & Aggregation

**Trade-off**: Full-fidelity metrics → high cardinality → cost/performance issues.

**Strategy**:
1. **Head-based sampling** (10%): Sample 10% of all requests uniformly
2. **Tail-based sampling** (100% for p95+): Keep all requests where `duration > p95_threshold` or `status >= 500`
3. **Exemplars**: Attach `trace_id` to histogram buckets for drill-down

**Cardinality Limits**:
- Max unique label combinations per metric: **10,000**
- Auto-drop labels exceeding limit (e.g., `user_id` → drop, use `user_tier` instead)
- See [logging_standard.md](logging_standard.md) for label guidelines

---

## 6. Dashboards & Visualization

### 6.1 Standard Dashboards

**Overview Dashboard** (`/web/obs/overview`):
- **RED Metrics** (Rate, Errors, Duration) per service
- **Error Budget Remaining** (gauge, 30d window)
- **Burn Rate Heatmap** (5m/1h/6h windows)

**Service Dashboard** (`/web/obs/service/{service_name}`):
- **SLI Trends** (30d): Availability, latency p50/p95/p99
- **Top Errors** (5xx breakdown by endpoint)
- **Trace Samples** (exemplar links to distributed traces)
- **Log Correlation** (error logs with `trace_id` links)

**Oncall Dashboard** (`/web/ops/oncall`):
- **Active Alerts** (inbox view, ACK/silence actions)
- **Error Budget Status** (all services, traffic light: green/yellow/red)
- **Recent Deployments** (correlation with SLI dips)

---

### 6.2 Example Panels

**Burn Rate Panel** (Grafana query):
```yaml
panel:
  title: "Error Budget Burn Rate (decision-api)"
  targets:
    - expr: |
        (
          1 - (
            sum(rate(http_requests_total{service="decision-api",status=~"2.."}[1h]))
            /
            sum(rate(http_requests_total{service="decision-api"}[1h]))
          )
        ) / (1 - 0.999)
      legend: "1h window"
    - expr: |
        # Same formula with [6h] window
      legend: "6h window"
  thresholds:
    - value: 1.0
      color: yellow
    - value: 2.0
      color: red
```

---

## 7. CLI Commands (dosctl)

**List SLOs**:
```bash
dosctl obs slo ls --service decision-api

Output:
SERVICE         SLI              TARGET   ACTUAL (30d)   BUDGET REMAINING
decision-api    availability     99.9%    99.85%         50.0%
decision-api    latency_p95      500ms    480ms          N/A (latency: pass/fail)
```

**Set SLO** (requires approval workflow):
```bash
dosctl obs slo set \
  --service decision-api \
  --sli availability \
  --target 99.95 \
  --window 30d \
  --reason "Upgrade to P0 criticality per EXEC-2025-Q4"
```

**Check Error Budget**:
```bash
dosctl obs eb status --service decision-api

Output:
Error Budget Status (decision-api, 30d window):
  SLO Target:           99.9%
  Actual Availability:  99.85%
  Budget Consumed:      50.0% (21.6 / 43.2 minutes)
  Budget Remaining:     50.0% (21.6 minutes)
  Burn Rate (1h):       0.8x
  Burn Rate (6h):       1.2x
  Gate Decision:        ALLOW ✅
```

**Query SLI**:
```bash
dosctl obs sli query \
  --service decision-api \
  --metric availability \
  --from 2025-10-01 \
  --to 2025-11-01 \
  --format csv > sli_report.csv
```

---

## 8. Compliance & Audit

**Audit Trail**:
- All SLO changes logged to `audit_slo_changes` table (RFC link, approver, timestamp)
- Error budget overrides logged to `audit_eb_overrides` (reason, approvers, duration)

**Quarterly Review**:
- SRE team presents SLO achievement report to Eng leadership
- Services consistently exceeding SLO by >1% → consider tightening (invest error budget in features)
- Services missing SLO → remediation plan required

**Regulatory (if applicable)**:
- Audit completeness SLO (100%) supports regulatory "explainability" requirements
- Billing reconciliation error (<0.01%) supports SOX compliance

---

## 9. References

- [Error Budget Policy](error_budget_policy.md) — Gating rules, exception process
- [Oncall Runbooks](ops/runbook_oncall.md) — P0/P1 response procedures
- [SLA Policies](sla_policies.md) — Customer-facing SLAs (vs. internal SLOs)
- [Logging Standard](logging_standard.md) — Structured logging, PII scrubbing
- **External**: [Google SRE Book — SLOs](https://sre.google/sre-book/service-level-objectives/)
- **External**: [Implementing SLOs (O'Reilly)](https://www.oreilly.com/library/view/implementing-service-level/9781492076803/)

---

## 10. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2025-11-04 | Platform Obs Team | Gate-T: Add burn-rate alerts, multi-window strategy, error budget gating API |
| 1.1.0 | 2025-09-15 | SRE Team | Add HITL queue SLOs, billing reconciliation SLI |
| 1.0.0 | 2025-06-01 | SRE Team | Initial catalog: decision-api, guardrails, ETL, catalog-search |

---

**END OF DOCUMENT**
