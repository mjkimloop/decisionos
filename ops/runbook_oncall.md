# Oncall Runbook — Incident Response & Escalation

**Version**: 2.1.0
**Last Updated**: 2025-11-04
**Owner**: SRE Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This runbook guides **oncall engineers** through incident detection, triage, mitigation, and escalation for DecisionOS services. It covers:

- **Alert response** (P0/P1/P2 classification, immediate actions)
- **Common failure modes** (deployment issues, dependency failures, resource exhaustion)
- **Rollback & canary procedures**
- **Escalation paths** (when to page manager, engage vendors, declare major incident)
- **Communication protocols** (stakeholder updates, postmortem)

---

### 1.2 Oncall Rotation

**Schedule**: 7-day rotations, 24/7 coverage
- **Primary oncall**: First responder (PagerDuty)
- **Secondary oncall**: Backup (15-min SLA if primary doesn't ACK)
- **Escalation oncall**: Duty Manager (for P0 requiring exec decisions)

**Handoff**: Every Monday 09:00 UTC
- **Procedure**:
  1. Review open incidents from previous week
  2. Check SLO status (any services in `review` or `block`?)
  3. Review scheduled maintenance/deploys for the week
  4. Handoff call (15 min, previous + next oncall + SRE lead)

**Tools**:
- **PagerDuty**: Alert routing, escalation policies
- **Slack**: `#oncall` (alerts), `#incidents` (active incident coordination)
- **Dashboard**: [/web/ops/oncall](https://obs.decisionos.internal/web/ops/oncall)

---

### 1.3 Severity Levels

| Severity | Definition | Response SLA | Examples |
|----------|-----------|--------------|----------|
| **P0** | Complete service outage or data loss affecting production users | ACK: 5 min<br>Mitigate: 1 hour<br>Resolve: 4 hours | • decision-api returning 100% 5xx<br>• Database corruption detected<br>• Security breach (unauthorized access) |
| **P1** | Major degradation affecting significant user subset | ACK: 15 min<br>Mitigate: 4 hours<br>Resolve: 24 hours | • decision-api p95 latency > 2s<br>• ETL pipeline 2h behind SLA<br>• Guardrails false positive spike |
| **P2** | Minor degradation or single-component failure with workaround | ACK: 1 hour<br>Mitigate: 24 hours<br>Resolve: 72 hours | • Non-critical API endpoint intermittent 5xx<br>• Dashboard rendering slow<br>• Low disk space warning (70%) |
| **P3** | Informational, no immediate user impact | ACK: 4 hours<br>Resolve: Best effort | • Certificate expiring in 30 days<br>• Deprecated API usage detected |

**SLA Notes**:
- **ACK** (Acknowledge): Oncall confirms receipt, begins investigation
- **Mitigate**: User impact reduced (e.g., traffic shifted to healthy region)
- **Resolve**: Root cause fixed, service fully restored

---

## 2. Alert Response Workflow

### 2.1 Initial Response (First 5 Minutes)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ACKNOWLEDGE alert in PagerDuty (stop paging)             │
│    → Confirms you're on it, starts SLA clock                │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CHECK oncall dashboard for context                       │
│    /web/ops/oncall → Recent deploys? Other active alerts?   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CLASSIFY severity (P0/P1/P2)                             │
│    → Use table above + judgment                             │
│    → If unsure, assume higher severity (de-escalate later)  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. POST to #incidents (if P0/P1)                            │
│    "🚨 P0: decision-api 100% 5xx since 14:23 UTC.           │
│     Investigating. ETA 15min."                              │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. EXECUTE runbook for alert type (see Section 3)           │
│    → Follow checklist, document actions in incident thread  │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles**:
- **Safety first**: If unsure, escalate early. Never guess at critical actions (e.g., data deletion).
- **Communicate often**: Update `#incidents` every 15-30 min, even if "still investigating."
- **Document actions**: Helps postmortem, helps next oncall if issue recurs.

---

### 2.2 Common Diagnostic Commands

**Check service health**:
```bash
# Overall service status
dosctl status decision-api

# Recent error rate
dosctl obs sli query --service decision-api --metric availability --from -1h

# Tail logs for errors
dosctl logs tail decision-api --level error --since 30m

# Recent deployments
dosctl deploy history decision-api --limit 5
```

**Check resource usage**:
```bash
# CPU/Memory/Disk
kubectl top pods -n decision-api

# Pod status
kubectl get pods -n decision-api -o wide

# Events (crashes, OOMKills, etc.)
kubectl get events -n decision-api --sort-by='.lastTimestamp' | tail -20
```

**Check dependencies**:
```bash
# External dependencies health
dosctl deps status decision-api
# → Returns status of DB, cache, external APIs

# Network connectivity
dosctl net check decision-api --target postgres.internal
```

**Correlate with traces**:
```bash
# Find slow traces (p99)
dosctl obs traces query \
  --service decision-api \
  --min-duration 2s \
  --since 30m \
  --limit 10
```

---

## 3. Runbooks by Alert Type

### 3.1 High Error Rate (5xx Spike)

**Alert**: `HighErrorRate5xx` (P0 if >10%, P1 if >5%)

**Symptoms**:
- `http_requests_total{status=~"5.."}` spike
- Users seeing "Internal Server Error"

**Immediate Actions** (5 min):
1. **Check recent deploys**:
   ```bash
   dosctl deploy history decision-api --limit 3
   ```
   - If deploy in last 30 min → **likely cause**, proceed to rollback (Section 4.1)

2. **Check logs for stack traces**:
   ```bash
   dosctl logs tail decision-api --level error --since 30m | grep -A 10 "Exception"
   ```
   - Look for common error (e.g., `NullPointerException`, `TimeoutException`)

3. **Check dependencies**:
   ```bash
   dosctl deps status decision-api
   ```
   - If DB/cache/external API down → See Section 3.6 (Dependency Failure)

**Mitigation** (30 min):
- **If deploy-related**: Rollback (Section 4.1)
- **If dependency-related**: Shift traffic to healthy region, engage vendor
- **If unknown**: Increase logging verbosity, collect traces, escalate to dev team

**Escalation**:
- If no mitigation found in 30 min → Page **Secondary Oncall** + **Dev Team Lead** (find via PagerDuty escalation policy)

---

### 3.2 High Latency (p95 Degradation)

**Alert**: `HighLatencyP95` (P1 if p95 > 2×SLO, P2 if 1.5×SLO)

**Symptoms**:
- Slow response times
- Possible timeout errors from clients

**Immediate Actions**:
1. **Identify slow endpoints**:
   ```bash
   dosctl obs metrics query 'topk(5, rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]))'
   ```
   - Returns top 5 slowest endpoints

2. **Check resource saturation**:
   ```bash
   kubectl top pods -n decision-api
   ```
   - High CPU? → Possible hot loop, regex catastrophic backtracking
   - High memory? → Possible memory leak, large payloads

3. **Check database slow queries**:
   ```bash
   # PostgreSQL
   dosctl db slow-queries --service decision-api --since 30m
   ```
   - N+1 query? Missing index? Lock contention?

**Mitigation**:
- **High CPU/Memory**: Scale up replicas temporarily
  ```bash
  dosctl scale decision-api --replicas 10  # from baseline 5
  ```
- **Slow endpoint**: Disable endpoint via feature flag (if non-critical)
- **Slow query**: Add index (if safe), or kill long-running queries

**Escalation**:
- If scaling doesn't help → Database issue, engage **DB Oncall** (via PagerDuty)

---

### 3.3 Error Budget Burn Rate Alert

**Alert**: `ErrorBudgetHighBurn1h` (P1) or `ErrorBudgetCriticalBurn5m` (P0)

**Symptoms**:
- Error budget burning faster than sustainable
- May indicate gradual degradation (not sudden outage)

**Immediate Actions**:
1. **Check burn rate dashboard**:
   ```
   /web/obs/service/decision-api → Error Budget panel
   ```
   - What's the root cause? (5xx? Latency? Both?)

2. **Identify time of degradation**:
   ```bash
   # When did error rate start increasing?
   dosctl obs metrics query 'rate(http_requests_total{status=~"5.."}[5m])' --since 2h
   ```
   - Gradual (over hours) → Possible resource leak, traffic growth
   - Sudden (< 5 min) → Deploy, config change, dependency failure

3. **Correlate with recent changes**:
   - Deploy? → Rollback
   - Config change? → Revert
   - Traffic spike? → Scale up, rate-limit

**Mitigation**:
- **P0 (5m window, burn rate >10)**: **Immediate rollback** (no investigation, restore service first)
- **P1 (1h window, burn rate >2)**: Investigate, mitigate within 4h, accept that deploy freeze may be triggered

**Escalation**:
- If burn rate continues after mitigation → **Duty Manager** (may need to grant error budget override for P0 fix)

---

### 3.4 Guardrails Block Rate Spike

**Alert**: `GuardrailsHighBlockRate` (P1 if block rate >10× baseline)

**Symptoms**:
- Sudden spike in requests blocked by guardrails
- Users seeing "Request denied due to policy violation" errors

**Immediate Actions**:
1. **Check guardrails dashboard**:
   ```
   /web/obs/service/guardrails → Block Rate by Rule
   ```
   - Which rule is blocking? (PII detection? Toxicity? Prompt injection?)

2. **Sample blocked requests**:
   ```bash
   dosctl guardrails blocked-samples --rule pii_detection --limit 10
   ```
   - Are these legitimate blocks (PII in user input) or false positives?

3. **Check recent rule changes**:
   ```bash
   dosctl guardrails rule history --since 24h
   ```
   - Did someone update a rule? (Regex change, threshold change)

**Mitigation**:
- **If false positives**: Revert rule change, or adjust threshold
  ```bash
  dosctl guardrails rule update pii_detection --threshold 0.9  # from 0.7
  ```
- **If legitimate blocks**: Possible attack (spam, abuse) → Alert security team, consider rate-limiting source IPs

**Escalation**:
- If rule change by compliance team (e.g., new PII pattern) → Engage **Compliance Officer** (may need exception for certain use cases)

---

### 3.5 ETL Pipeline Freshness Lag

**Alert**: `ETLFreshnessLagHigh` (P1 if lag >30 min, P2 if >15 min)

**Symptoms**:
- Data in analytics/ML models is stale
- Underwriting decisions may use outdated credit scores

**Immediate Actions**:
1. **Check pipeline status**:
   ```bash
   dosctl pipeline status etl-pipeline
   ```
   - Which stage is lagging? (Kafka consumer? Spark job? DB write?)

2. **Check Kafka consumer lag**:
   ```bash
   dosctl kafka consumer-lag --group etl-pipeline
   ```
   - Lag in millions? → Consumer can't keep up with producer

3. **Check resource usage**:
   ```bash
   kubectl top pods -n etl-pipeline
   ```
   - Out of memory? CPU throttled?

**Mitigation**:
- **High consumer lag**: Scale up consumer replicas
  ```bash
  dosctl scale etl-pipeline --replicas 20  # from 10
  ```
- **Slow Spark job**: Check query plan, add caching, repartition data
- **DB write bottleneck**: Check for locks, add connection pool

**Escalation**:
- If lag continues to grow → **Data Engineering Oncall** (via PagerDuty)

---

### 3.6 Dependency Failure (External API Down)

**Alert**: `DependencyUnavailable` (P0 if critical dependency, P1 if non-critical)

**Symptoms**:
- External API (e.g., Auth0, payment gateway) returning errors
- decision-api timing out on calls to dependency

**Immediate Actions**:
1. **Confirm dependency status**:
   ```bash
   dosctl deps status decision-api
   # Or check vendor status page (e.g., status.auth0.com)
   ```

2. **Check circuit breaker**:
   ```bash
   dosctl circuit-breaker status --service decision-api --dependency auth0
   ```
   - Is circuit open? (Failing fast to preserve our resources)

3. **Check fallback logic**:
   - Does service have degraded mode? (e.g., skip optional feature, use cached data)

**Mitigation**:
- **If vendor outage**:
  - Enable degraded mode (if available)
  - Communicate to users (e.g., "Login temporarily unavailable, trying again in 5 min")
  - Engage vendor support, get ETA
- **If no fallback**:
  - Return user-friendly error, log for retry
  - Avoid cascading failure (set aggressive timeouts, open circuit breaker)

**Escalation**:
- **Vendor SLA breach**: Escalate to **Vendor Manager** (track SLA credits)
- **Critical dependency, no fallback**: Consider **Major Incident** declaration (Section 5)

---

### 3.7 Database Issues (Slow Queries, Connection Pool Exhausted)

**Alert**: `DatabaseSlowQueries` (P1) or `DatabaseConnectionPoolExhausted` (P0)

**Symptoms**:
- Queries taking >10s (normally <100ms)
- Connection pool full (all connections in use)

**Immediate Actions**:
1. **Check active connections**:
   ```bash
   dosctl db connections --service decision-api
   # Shows active queries, idle connections
   ```

2. **Identify slow queries**:
   ```bash
   dosctl db slow-queries --since 30m
   ```
   - Which query? (Look for full table scan, missing index)

3. **Check for locks**:
   ```bash
   dosctl db locks
   # Shows blocked queries, which locks they're waiting on
   ```

**Mitigation**:
- **Connection pool exhausted**:
  - Scale up app replicas (more pools)
  - Increase pool size (if DB can handle it)
  - Kill idle connections: `dosctl db kill-idle --idle-time 5m`
- **Slow query**:
  - Add index (if schema allows, low-risk)
  - Kill long-running query (if safe): `dosctl db kill-query <pid>`
  - Rewrite query (needs dev team)

**Escalation**:
- If locks persist → **DBA Oncall** (may need to restart DB, risky)
- If corruption suspected → **P0 escalation**, do NOT attempt fixes without DBA

---

### 3.8 Security Alert (Unauthorized Access, Breach)

**Alert**: `SecurityUnauthorizedAccess` (always P0)

**Symptoms**:
- Audit log shows access from unknown IP
- User reports account compromise
- Security tool (e.g., intrusion detection) flags anomaly

**Immediate Actions**:
1. **DO NOT investigate alone** → Immediately page **Security Oncall** (via PagerDuty)
2. **Preserve evidence**:
   - Do NOT restart pods, clear logs, or "clean up"
   - Snapshot logs: `dosctl logs snapshot decision-api --since 24h --output /secure/incident-logs/`
3. **Isolate affected resources**:
   - If specific user account: Lock account
   - If specific pod: Quarantine (remove from load balancer, keep running for forensics)

**Mitigation**:
- **Security Oncall leads** (oncall engineer supports)
- Possible actions: Rotate credentials, revoke tokens, block IPs, deploy patches

**Escalation**:
- **Security Oncall** (immediate)
- **CISO** (within 1h, if breach confirmed)
- **Legal** (if PII/PHI involved, per compliance policy)

**Documentation**:
- All actions logged in incident tracker (Jira/ServiceNow)
- Postmortem required within 48h (see Section 6)

---

## 4. Common Procedures

### 4.1 Rollback Deployment

**When**: Recent deploy (<30 min) correlates with incident.

**Procedure**:

```bash
# 1. Get current version
dosctl deploy status decision-api

# Output:
# Current: v2.34.5 (deployed 10 min ago)
# Previous: v2.34.4

# 2. Check previous version stability (was it green before?)
dosctl obs sli query --service decision-api --from -24h --to -1h
# → Verify v2.34.4 had >99.9% availability

# 3. Rollback
dosctl deploy rollback decision-api --to-version v2.34.4

# 4. Monitor rollback
watch dosctl deploy status decision-api
# Wait for all pods to be ready

# 5. Verify error rate drops
dosctl obs metrics query 'rate(http_requests_total{service="decision-api",status=~"5.."}[5m])'
```

**Timeline**:
- **Rollback initiated**: < 5 min from decision
- **Rollback complete**: < 10 min (depends on pod startup time)
- **Service restored**: < 15 min (allow traffic to shift to healthy pods)

**Communication**:
```
#incidents: "Rolling back decision-api to v2.34.4. ETA 10 min."
[10 min later]: "Rollback complete. Error rate back to baseline. Root cause: NPE in new validation logic. Dev team investigating."
```

---

### 4.2 Canary Rollback (Partial Deploy Failing)

**When**: Canary (e.g., 10% traffic) shows elevated errors, but main fleet is healthy.

**Procedure**:

```bash
# 1. Check canary status
dosctl deploy canary status decision-api

# Output:
# Canary: v2.34.5 (10% traffic, error rate 8%) ❌
# Stable: v2.34.4 (90% traffic, error rate 0.5%) ✅

# 2. Halt canary progression (prevent auto-scale to 100%)
dosctl deploy canary pause decision-api

# 3. Set canary traffic to 0%
dosctl deploy canary set decision-api --traffic 0

# 4. Verify stable version handles 100% traffic
dosctl obs metrics query 'rate(http_requests_total{service="decision-api",version="v2.34.4"}[5m])'

# 5. Abort canary deployment
dosctl deploy canary abort decision-api --version v2.34.5
```

**Outcome**: New version (v2.34.5) is discarded, all traffic stays on stable version (v2.34.4).

---

### 4.3 Scale Up Resources

**When**: Resource saturation (CPU >80%, Memory >90%, or connection pool exhausted).

**Procedure**:

```bash
# 1. Scale horizontal (add replicas)
dosctl scale decision-api --replicas 10  # from baseline 5

# 2. Verify new pods are healthy
kubectl get pods -n decision-api -w
# Wait for all 10 pods to be Running + Ready

# 3. Monitor resource usage
kubectl top pods -n decision-api
# Verify CPU/Memory spread across pods

# 4. If still saturated, scale vertical (increase pod resources)
dosctl scale decision-api --cpu 4 --memory 8Gi  # from 2 CPU, 4Gi
# Note: Requires pod restart, brief disruption
```

**Revert**:
- After incident resolved, scale back to baseline (avoid cost overrun)
- Schedule during low-traffic period (early morning UTC)

---

### 4.4 Enable Circuit Breaker / Degraded Mode

**When**: Dependency is down, and we want to fail fast (avoid timeouts, resource exhaustion).

**Procedure**:

```bash
# 1. Check circuit breaker status
dosctl circuit-breaker status --service decision-api --dependency auth0

# Output:
# Status: closed (allowing requests)
# Failure rate (5m): 80% (threshold: 50%)
# Recommendation: OPEN circuit

# 2. Force circuit open (manual override)
dosctl circuit-breaker open --service decision-api --dependency auth0

# 3. Verify requests fail fast
dosctl logs tail decision-api --filter "circuit breaker open" --since 1m
# Should see logs like: "auth0 circuit open, returning cached profile"

# 4. Monitor dependency recovery
dosctl deps status decision-api
# When auth0 returns to healthy, circuit breaker will auto-close (half-open → closed)
```

**Degraded Mode** (if available):
```bash
# Example: Skip optional recommendations, serve core decision only
dosctl feature-flag set decision-api --flag skip_recommendations --value true
```

---

### 4.5 Silence False-Positive Alerts

**When**: Alert firing, but confirmed non-issue (e.g., planned load test, expected traffic spike).

**Procedure**:

```bash
# 1. Acknowledge alert in PagerDuty
# (Stops paging, but alert still visible)

# 2. Silence alert in Alertmanager (if recurring)
dosctl obs alerts silence \
  --name HighLatencyP95 \
  --service decision-api \
  --duration 2h \
  --reason "Load test in progress, expected latency spike"

# 3. Notify team
# Post in #oncall: "Silencing HighLatencyP95 for 2h due to planned load test."

# 4. After test, verify alert un-silences automatically
# (or manually un-silence if test finishes early)
```

**Warning**: Do NOT silence alerts without documenting reason. Leads to alert fatigue and missed real incidents.

---

## 5. Major Incident Declaration

### 5.1 When to Declare Major Incident

**Criteria** (any of):
- **P0 incident** lasting >1 hour (despite mitigation attempts)
- **Multi-service outage** (e.g., decision-api + guardrails both down)
- **Data loss** confirmed or suspected
- **Security breach** confirmed (unauthorized access, data exfiltration)
- **Regulatory impact** (e.g., audit trail corruption, SLA breach with financial penalty)
- **Executive request** (VP/CEO requests major incident process)

**Major Incident** triggers:
- Dedicated Slack war room (`#incident-<timestamp>`)
- Incident Commander assigned (Senior SRE or Eng Manager)
- Scribe assigned (document timeline, decisions)
- Stakeholder updates every 30 min (internal) + every 2h (external, if needed)

---

### 5.2 Major Incident Roles

| Role | Responsibilities | Assigned To |
|------|-----------------|-------------|
| **Incident Commander (IC)** | Owns incident, makes decisions, coordinates teams | Senior SRE or Eng Manager |
| **Oncall Engineer** | Technical lead, executes mitigation | Current oncall |
| **Scribe** | Documents timeline, decisions, action items | Junior SRE or Ops |
| **Communications Lead** | Stakeholder updates (internal/external) | PM or Customer Success |
| **Subject Matter Expert (SME)** | Domain expertise (DB, network, security) | Called in as needed |

---

### 5.3 Major Incident Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DECLARE major incident (oncall or manager)               │
│    dosctl incident declare --title "decision-api outage"    │
│    → Creates Slack war room, assigns IC                     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. IC ASSEMBLES team (war room invite)                      │
│    • Oncall (technical lead)                                │
│    • Scribe (timeline documentation)                        │
│    • Comms (stakeholder updates)                            │
│    • SMEs (as needed: DBA, network, security)               │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. SCRIBE creates incident doc (live timeline)              │
│    Template: https://wiki/incident-template                 │
│    • What happened? (symptoms, timeline)                    │
│    • Current status (mitigation in progress)                │
│    • Actions taken (rollback, scaled up, etc.)              │
│    • Next steps                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. COMMS posts initial update (#incidents, stakeholders)    │
│    "🚨 Major incident: decision-api experiencing 100% 5xx.  │
│     Impact: All lending decisions failing.                  │
│     Mitigation: Rollback in progress, ETA 15 min.           │
│     Next update: 30 min."                                   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. ONCALL executes mitigation (IC coordinates)              │
│    • Rollback, scale up, shift traffic, etc.                │
│    • IC makes go/no-go decisions                            │
│    • Scribe documents all actions + timestamps              │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. SERVICE RESTORED (incident not yet closed)               │
│    • Comms: "Service restored at 15:34 UTC. Monitoring."    │
│    • Oncall: Monitor for 1h (ensure stability)              │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. CLOSE incident (after 1h stable)                         │
│    dosctl incident close <incident_id>                      │
│    • Final update to stakeholders                           │
│    • Schedule postmortem (within 48h)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Postmortem Process

### 6.1 When Postmortem is Required

**Mandatory**:
- All P0 incidents
- Any incident with user-visible impact >15 min
- Security incidents
- Error budget breaches (SLO missed)

**Optional** (but recommended):
- P1 incidents (learning opportunity)
- Near-misses (caught before user impact)

---

### 6.2 Postmortem Template

**Document**: [Postmortem Template (Google Doc)](https://docs.google.com/document/d/TEMPLATE_ID)

**Sections**:
1. **Summary** (2-3 sentences: what happened, impact, resolution)
2. **Timeline** (from scribe notes, with timestamps)
3. **Root Cause** (5 Whys analysis)
4. **Impact** (users affected, revenue loss, SLO breach)
5. **What Went Well** (detection, mitigation speed, communication)
6. **What Went Wrong** (gaps, delays, confusion)
7. **Action Items** (with owners, due dates)
   - Preventative (stop this from happening again)
   - Detective (catch it faster next time)
   - Process (improve runbooks, alerts, documentation)

**Example Action Items**:
```
- [ ] Add integration test for retry logic (Eng: Alice, Due: 2025-11-15)
- [ ] Add canary metric: error rate by version (SRE: Bob, Due: 2025-11-10)
- [ ] Update runbook with "check recent config changes" step (Oncall: Charlie, Due: 2025-11-08)
```

---

### 6.3 Postmortem Review Meeting

**Attendees**:
- Incident participants (IC, oncall, SMEs)
- Service owners (dev team)
- SRE lead
- Optional: PM, Eng Manager (if process/tooling issues)

**Agenda** (60 min):
1. **Read postmortem** (async before meeting, 5 min recap)
2. **Discuss root cause** (15 min)
3. **Review action items** (20 min)
   - Are they actionable? (Specific, measurable, assignable)
   - Prioritization (P0 fixes vs. nice-to-haves)
4. **Process feedback** (10 min)
   - What would make oncall easier? (Tooling, documentation, training)
5. **Assign owners & due dates** (10 min)

**Output**:
- Finalized postmortem published to wiki
- Action items tracked in Jira/Linear
- Lessons learned shared at All-Hands or Eng Sync

---

## 7. Escalation Paths

### 7.1 Escalation Matrix

| Scenario | Escalate To | Method | SLA |
|----------|-------------|--------|-----|
| **P0, no mitigation in 30 min** | Secondary Oncall | PagerDuty escalation policy | 5 min ACK |
| **P0, dev team needed** | Dev Team Lead (for service) | PagerDuty override | 15 min ACK |
| **Database issue** | DBA Oncall | PagerDuty "Database" service | 10 min ACK |
| **Security incident** | Security Oncall | PagerDuty "Security" service | Immediate |
| **Vendor SLA breach** | Vendor Manager | Slack DM + Email | 1 hour |
| **Major incident (multi-service)** | Duty Manager | PagerDuty "Escalation Oncall" | 10 min ACK |
| **Need error budget override** | Duty Manager | Slack `#oncall` + PagerDuty | 30 min |
| **Exec decision needed** (e.g., take full outage to prevent data loss) | VP Engineering or CTO | Phone call (emergency contact list) | Immediate |

---

### 7.2 After-Hours Escalation

**Policy**: Oncall engineers empowered to page anyone needed for P0/P1.

**Guidelines**:
- **P0**: Page immediately, no hesitation (people expect to be woken for P0)
- **P1**: Page during business hours, or if impacting SLA/error budget significantly
- **P2**: Do NOT page after-hours (handle during next business day)

**Courtesy**:
- Use PagerDuty (not personal cell) so it's logged
- If paging exec (VP/CTO), send Slack summary first (if they don't ACK in 5 min, call)

---

## 8. Oncall Best Practices

### 8.1 Preparation (Before Your Shift)

**48 hours before**:
- [ ] Review open incidents from previous week
- [ ] Check SLO status (any services in yellow/red?)
- [ ] Review deploy schedule (any high-risk deploys during your shift?)
- [ ] Test PagerDuty (send test alert, verify phone/SMS/app works)

**Handoff call** (Monday 09:00 UTC):
- [ ] Previous oncall summarizes week (incidents, trends, known issues)
- [ ] Review action items (anything you need to follow up on?)
- [ ] Ask questions (unfamiliar service? Need training?)

---

### 8.2 During Your Shift

**Proactive**:
- Check oncall dashboard daily (morning, mid-day, evening)
- Triage P2/P3 alerts (file bugs, silence noise)
- Update runbooks when you find gaps

**Reactive**:
- Respond to alerts per SLA (P0: 5min, P1: 15min, P2: 1h)
- Document actions (even if "investigated, false alarm")
- Escalate early if unsure

**Self-Care**:
- **Sleep**: If paged at 3am, take comp time next day
- **Breaks**: Oncall is stressful, step away between incidents
- **Ask for help**: Secondary oncall exists for a reason

---

### 8.3 After Your Shift

**Handoff**:
- Write summary of your week (incidents, trends, improvements)
- Flag any follow-ups for next oncall
- Celebrate wins (fast mitigation, good postmortem, runbook improvement)

**Retrospective** (monthly, all oncalls):
- What incidents were most stressful? (How to improve?)
- What alerts are noisy? (Tune or silence)
- What training is needed? (Gamedays, shadowing, workshops)

---

## 9. Communication Templates

### 9.1 Incident Update (Slack)

**Initial** (within 5 min of P0/P1):
```
🚨 P0 Incident: decision-api outage
Impact: 100% of lending decisions failing since 14:23 UTC
Mitigation: Rollback to v2.34.4 in progress, ETA 10 min
Next update: 15 min
Incident doc: <link>
```

**Progress Update** (every 15-30 min):
```
Update (14:40 UTC): Rollback complete, error rate dropping.
Current: 20% errors (down from 100%)
Next: Monitor for 10 min, verify full recovery
Next update: 15:00 UTC
```

**Resolution**:
```
✅ Resolved (15:05 UTC): decision-api restored to baseline.
Root cause: NullPointerException in new validation logic (v2.34.5)
Duration: 42 min
Impact: ~500 users saw errors, 120 decisions failed (retries successful)
Postmortem: Scheduled for 2025-11-06 10:00 UTC
Thank you for patience!
```

---

### 9.2 External Communication (Customers)

**When**: User-visible outage >30 min, or SLA breach

**Template** (status page update):
```
[Posted 14:30 UTC]
We are currently investigating an issue affecting loan application decisions.
Users may see "Internal Server Error" when submitting applications.
Our team is actively working on a resolution. We will provide updates every 30 minutes.

[Updated 15:00 UTC]
The issue has been identified and a fix is being deployed.
We expect full resolution within 15 minutes.

[Resolved 15:10 UTC]
The issue has been resolved. All services are operating normally.
Affected users: Applications submitted between 14:23-15:05 UTC may have failed.
Please retry your application. We apologize for the inconvenience.
```

**Tone**: Professional, transparent, empathetic (avoid jargon, blame, excuses).

---

## 10. Tools Reference

### 10.1 Primary Tools

| Tool | Purpose | URL / Command |
|------|---------|---------------|
| **PagerDuty** | Alert routing, escalation | https://decisionos.pagerduty.com |
| **Oncall Dashboard** | Alert inbox, SLO status, recent deploys | https://obs.decisionos.internal/web/ops/oncall |
| **Grafana** | Metrics, dashboards | https://grafana.decisionos.internal |
| **Loki** | Log aggregation, search | `dosctl logs tail <service>` |
| **Jaeger** | Distributed tracing | https://jaeger.decisionos.internal |
| **dosctl** | CLI for ops (deploy, scale, logs, db) | `dosctl --help` |
| **kubectl** | Kubernetes ops | `kubectl --context prod` |

---

### 10.2 dosctl Quick Reference

```bash
# Service status
dosctl status <service>

# Deployments
dosctl deploy history <service>
dosctl deploy rollback <service> --to-version <ver>
dosctl deploy canary status <service>

# Scaling
dosctl scale <service> --replicas <N>

# Logs
dosctl logs tail <service> --level error --since 30m
dosctl logs search <service> --query "NullPointerException"

# Observability
dosctl obs sli query --service <svc> --metric availability --from -1h
dosctl obs eb status --service <svc>
dosctl obs traces query --service <svc> --min-duration 2s

# Database
dosctl db slow-queries --service <svc> --since 30m
dosctl db connections <svc>
dosctl db locks

# Dependencies
dosctl deps status <service>
dosctl circuit-breaker status --service <svc> --dependency <dep>

# Incidents
dosctl incident declare --title "..."
dosctl incident close <incident_id>
```

---

## 11. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.1.0 | 2025-11-04 | SRE Team | Gate-T: Add error budget burn rate runbook, major incident workflow |
| 2.0.0 | 2025-09-01 | SRE Team | Add security incident procedure, postmortem template |
| 1.5.0 | 2025-07-15 | SRE Team | Add ETL pipeline, guardrails runbooks |
| 1.0.0 | 2025-05-01 | SRE Team | Initial oncall runbook |

---

**END OF DOCUMENT**

**Emergency Contacts**: See internal wiki `/oncall/contacts` (not stored in public repo).
