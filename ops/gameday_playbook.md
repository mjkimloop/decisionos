# GameDay Playbook — Chaos Engineering & Incident Drills

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Owner**: SRE Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

**GameDay exercises** are controlled chaos experiments to:
1. **Validate resilience**: Test that circuit breakers, retries, failovers actually work
2. **Train teams**: Practice incident response in low-stakes environment
3. **Find gaps**: Discover missing runbooks, alerts, observability
4. **Build confidence**: Reduce fear of production incidents

**Principle**: *"Hope is not a strategy."* We test in prod (controlled), before users find bugs for us.

---

### 1.2 GameDay Types

| Type | Scope | Frequency | Participants | Duration |
|------|-------|-----------|--------------|----------|
| **Tabletop** | Walkthrough scenario, no actual failures | Monthly | Oncall + SRE | 1 hour |
| **Canary Chaos** | Inject failures in canary environment (10% traffic) | Bi-weekly | SRE + Dev | 2 hours |
| **Full Chaos** | Inject failures in production (controlled blast radius) | Quarterly | SRE + Dev + PM | 4 hours |
| **Red Team** | Security-focused (pen-test, social engineering) | Annually | Security + SRE | 1 day |

**This playbook covers**: Scenarios, procedures, safety rails, postmortem templates.

---

### 1.3 Safety Principles

**Rules**:
1. **Announce in advance**: Post in `#gameday` channel 48h before (except Red Team)
2. **Business hours only**: Tue-Thu, 10:00-16:00 UTC (avoid Mon/Fri, weekends, holidays)
3. **Abort criteria**: Define BEFORE starting (e.g., "if error rate >5%, abort")
4. **Rollback ready**: One-click revert (kill chaos process, restore config)
5. **Stakeholder buy-in**: PM + Eng Manager approve (they accept user-visible impact risk)

**Blast Radius Limits**:
- **Canary Chaos**: Max 10% traffic, non-revenue-critical flows
- **Full Chaos**: Max 20% traffic, abort if SLO breach imminent
- **Never**: Delete data, modify billing, trigger real alerts to customers

---

## 2. GameDay Scenarios

### Scenario 1: Database Failover (P0 Simulation)

**Objective**: Validate that decision-api survives primary DB failure (failover to replica).

**Hypothesis**: "Failover completes in <30s, app auto-reconnects, <1% failed requests."

**Participants**: SRE (chaos operator), Dev (app owner), DBA (DB expert)

**Pre-Flight Checklist**:
- [ ] Replica lag <5s (verify with `dosctl db replica-lag`)
- [ ] Failover tested in staging last week (success)
- [ ] Oncall notified (they'll see alerts, but know it's drill)
- [ ] Abort command ready: `dosctl chaos abort db-failover-001`

**Procedure**:

```bash
# 1. Baseline metrics (before chaos)
dosctl obs sli query --service decision-api --metric availability --from -10m
# Expected: 99.9%+

# 2. Inject failure: Promote replica to primary
dosctl chaos inject db-failover \
  --target postgres-primary \
  --duration 5m \
  --experiment-id db-failover-001

# What happens:
# - Primary DB marked unhealthy (simulated crash)
# - Replica promoted to primary
# - App connection pool detects failure, reconnects to new primary

# 3. Monitor (real-time dashboard)
# /web/obs/service/decision-api → Watch error rate, latency
# Expected: Brief spike (<30s), then recovery

# 4. Observe alerts (should fire, then auto-resolve)
# PagerDuty: "DatabasePrimaryDown" alert (P1)
# → Oncall acknowledges, sees #gameday tag, no action needed

# 5. After 5 min, restore (auto-revert)
# dosctl chaos status db-failover-001
# Output: "Experiment ended, restored at 14:35 UTC"

# 6. Verify metrics
dosctl obs sli query --service decision-api --metric availability --from -10m
# Expected: >99% (allow 0.5% dip during failover)
```

**Success Criteria**:
- [x] Failover completed in <30s
- [x] Error rate <5% during failover window
- [x] No manual intervention needed (auto-reconnect worked)
- [x] Alert fired and auto-resolved

**Failure Case** (Example):
```
Result: ❌ Failed
Observed: Error rate spiked to 80% for 2 minutes (60s longer than expected)
Root Cause: Connection pool didn't detect failure fast enough (health check interval: 60s)
Action Items:
  - Reduce health check interval to 10s (DEV-1234)
  - Add app-level circuit breaker for DB calls (DEV-1235)
  - Rerun GameDay after fixes (scheduled: 2025-11-15)
```

---

### Scenario 2: Dependency Timeout (External API Slow)

**Objective**: Validate circuit breaker for external auth API (Auth0).

**Hypothesis**: "Circuit breaker opens after 50% failures, app degrades gracefully (cached profiles), <10s user impact."

**Participants**: SRE, Dev (auth owner)

**Pre-Flight Checklist**:
- [ ] Feature flag `use_cached_auth` enabled (fallback mode)
- [ ] Cache hit rate >80% (verify users likely to have cached profiles)
- [ ] Abort command ready: `dosctl chaos abort auth-timeout-001`

**Procedure**:

```bash
# 1. Inject latency: Auth0 responses delayed by 5s (timeout: 2s)
dosctl chaos inject latency \
  --target auth0.external \
  --delay 5s \
  --duration 3m \
  --experiment-id auth-timeout-001

# What happens:
# - decision-api calls to Auth0 timeout after 2s
# - After 5 consecutive timeouts (10s total), circuit breaker opens
# - App switches to cached profiles (degraded mode)

# 2. Monitor circuit breaker
dosctl circuit-breaker status --service decision-api --dependency auth0
# Expected: "Status: open, Failure rate: 100%, Fallback: cache"

# 3. Verify user impact
dosctl obs metrics query 'rate(http_requests_total{service="decision-api",status="200"}[1m])'
# Expected: Success rate stays >95% (cached auth working)

# 4. End experiment (after 3 min)
# dosctl chaos end auth-timeout-001

# 5. Verify circuit breaker closes (Auth0 healthy again)
dosctl circuit-breaker status --service decision-api --dependency auth0
# Expected: "Status: half-open → closed, Failure rate: 0%"
```

**Success Criteria**:
- [x] Circuit breaker opened within 10s
- [x] Cached auth served 95%+ requests successfully
- [x] Circuit auto-closed after Auth0 recovered
- [x] Alert: "Auth0CircuitOpen" fired (P2, suppressed due to #gameday)

---

### Scenario 3: Traffic Spike (10× Load)

**Objective**: Validate auto-scaling + rate limiting under extreme load.

**Hypothesis**: "Auto-scaler provisions new pods within 2 min, rate limiter protects DB, p95 latency <2s."

**Participants**: SRE, Dev, Infra (cloud provider oncall on standby)

**Pre-Flight Checklist**:
- [ ] Auto-scaling enabled (min: 5 pods, max: 50 pods)
- [ ] Rate limiter: 1000 req/s per user (protects from single-user DOS)
- [ ] Budget approved (50 pods for 30 min = $X cost)
- [ ] Abort: `dosctl chaos abort traffic-spike-001`

**Procedure**:

```bash
# 1. Generate synthetic traffic (10× baseline)
dosctl chaos inject traffic-spike \
  --target decision-api \
  --rate 10x \
  --duration 30m \
  --experiment-id traffic-spike-001

# What happens:
# - Load balancer receives 5000 req/s (baseline: 500 req/s)
# - Auto-scaler detects CPU >70%, provisions new pods
# - Rate limiter throttles users exceeding 1000 req/s

# 2. Monitor auto-scaling
kubectl get hpa -n decision-api -w
# Expected: Replicas scale from 5 → 30+ within 2 min

# 3. Monitor latency
dosctl obs metrics query 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))'
# Expected: p95 < 2s (some queueing, but not catastrophic)

# 4. Monitor rate limiting
dosctl obs metrics query 'rate(http_requests_total{status="429"}[1m])'
# Expected: Some 429s (rate limit hit), but <5% of total

# 5. After 30 min, end experiment
# Traffic returns to baseline, auto-scaler scales down
```

**Success Criteria**:
- [x] Auto-scaler provisioned pods within 2 min
- [x] p95 latency stayed <2s (acceptable degradation)
- [x] Rate limiter protected DB (no connection pool exhaustion)
- [x] No manual intervention needed

**Failure Case** (Example):
```
Result: ⚠️ Partial Success
Observed: Auto-scaling worked, but p95 spiked to 5s for first 3 min
Root Cause: Cold start penalty (new pods take ~90s to warm up JVM)
Action Items:
  - Implement pod pre-warming (keep 2 spare pods hot) (INFRA-567)
  - Tune HPA to scale proactively (predict spikes via ML) (INFRA-568)
```

---

### Scenario 4: Network Partition (Region Isolation)

**Objective**: Validate multi-region failover (us-east-1 isolated, traffic shifts to us-west-2).

**Hypothesis**: "Traffic fails over within 60s, <2% failed requests, no data inconsistency."

**Participants**: SRE, Infra, DBA (multi-region expert)

**Pre-Flight Checklist**:
- [ ] Multi-region setup verified (us-east-1, us-west-2 both healthy)
- [ ] Data replication lag <10s (cross-region DB sync)
- [ ] DNS TTL: 30s (fast failover)
- [ ] Abort: `dosctl chaos abort network-partition-001`

**Procedure**:

```bash
# 1. Inject failure: Drop all traffic to us-east-1
dosctl chaos inject network-partition \
  --target us-east-1 \
  --duration 10m \
  --experiment-id network-partition-001

# What happens:
# - Load balancer health checks fail for us-east-1
# - DNS updated to point to us-west-2 only
# - New requests routed to us-west-2

# 2. Monitor failover
dosctl obs metrics query 'sum(rate(http_requests_total[1m])) by (region)'
# Expected: us-east-1 drops to 0, us-west-2 doubles

# 3. Verify data consistency
dosctl db consistency-check --region us-west-2
# Expected: "Replication lag: 5s, no conflicts"

# 4. After 10 min, restore us-east-1
# dosctl chaos end network-partition-001

# 5. Verify traffic rebalances
# Expected: 50/50 split across regions
```

**Success Criteria**:
- [x] Failover completed within 60s
- [x] Error rate <2% (brief DNS propagation delay)
- [x] No data loss or inconsistency

---

### Scenario 5: Cascading Failure (Retry Storm)

**Objective**: Test that retry logic doesn't cause cascading failure (retry storm → resource exhaustion).

**Hypothesis**: "Exponential backoff + jitter prevents retry storm, downstream service survives."

**Participants**: SRE, Dev (retry logic owner)

**Pre-Flight Checklist**:
- [ ] Retry config reviewed: `max_retries=3, backoff=exponential, jitter=±50%`
- [ ] Circuit breaker: opens after 50% failures
- [ ] Abort: `dosctl chaos abort cascading-failure-001`

**Procedure**:

```bash
# 1. Inject failure: Downstream API (risk-scoring) returns 50% 5xx
dosctl chaos inject error-rate \
  --target risk-scoring-api \
  --rate 0.5 \
  --duration 5m \
  --experiment-id cascading-failure-001

# What happens:
# - decision-api receives 50% errors from risk-scoring
# - Retries triggered (up to 3× per request)
# - If retry logic bad: 1 request → 4 attempts (1 + 3 retries) → 4× load on risk-scoring → death spiral

# 2. Monitor downstream load
dosctl obs metrics query 'rate(http_requests_total{service="risk-scoring-api"}[1m])'
# Expected: Slight increase (retries), but NOT 4× (exponential backoff + circuit breaker should limit)

# 3. Monitor circuit breaker
dosctl circuit-breaker status --service decision-api --dependency risk-scoring-api
# Expected: "Status: open" (after 50% failures, circuit opens, stops retries)

# 4. Verify decision-api doesn't crash
kubectl get pods -n decision-api
# Expected: All pods healthy (no OOMKill, CPU throttling)

# 5. End experiment, verify recovery
```

**Success Criteria**:
- [x] Retry storm avoided (downstream load <2× baseline)
- [x] Circuit breaker opened (stopped futile retries)
- [x] decision-api remained healthy

**Failure Case** (Example):
```
Result: ❌ Failed
Observed: risk-scoring-api load spiked to 10× baseline, crashed
Root Cause: Retry logic had no jitter, all clients retried simultaneously
Action Items:
  - Add jitter to retry backoff (±50%) (DEV-9999)
  - Reduce max_retries from 3 → 2 (DEV-9998)
  - Rerun GameDay after fixes
```

---

## 3. Tabletop Exercise (No Real Failures)

### 3.1 Format

**Duration**: 60 minutes
**Frequency**: Monthly (first Tuesday, 10:00 UTC)
**Participants**: Oncall rotation (primary + secondary), SRE lead, volunteer dev

**Structure**:
1. **Scenario presented** (15 min): Facilitator describes incident (e.g., "Database is down, error rate 100%")
2. **Team responds** (30 min): Participants walk through actions (no actual commands, just discussion)
   - What would you check first?
   - What's the rollback procedure?
   - When would you escalate?
3. **Debrief** (15 min): Gaps identified (missing runbook steps, unclear ownership)

---

### 3.2 Example Tabletop Scenario

**Scenario**: *"It's 02:00 UTC. PagerDuty pages you: decision-api error rate is 80%. Recent deploy 30 min ago (v2.45.1). What do you do?"*

**Expected Response**:
1. **ACK alert** (PagerDuty, stop paging)
2. **Check oncall dashboard**: Recent deploy? Yes, v2.45.1 30 min ago.
3. **Check logs**: `dosctl logs tail decision-api --level error --since 30m`
   - Find: `NullPointerException in CreditScoreValidator`
4. **Decision**: Rollback (deploy is suspect, clear error in logs)
5. **Execute**: `dosctl deploy rollback decision-api --to-version v2.45.0`
6. **Monitor**: Error rate drops to 0% within 5 min
7. **Communicate**: Post to `#incidents`: "Rolled back v2.45.1 due to NPE. Service restored."
8. **Follow-up**: File bug, schedule postmortem

**Debrief Questions**:
- Q: "What if rollback didn't work?"
  - A: Escalate to dev team lead, check if issue existed in v2.45.0 too (maybe data corruption?)
- Q: "What if this happened during business hours?"
  - A: Same procedure, but communicate to PM (users may see errors, prepare comms)

**Outcome**: Oncall team gains confidence, identifies that runbook doesn't cover "rollback didn't work" scenario → Action item to update runbook.

---

## 4. GameDay Execution Checklist

### 4.1 Pre-GameDay (T-48h)

- [ ] **Select scenario** (from Section 2, or create new)
- [ ] **Assign roles**:
  - **Chaos Operator** (injects failures, monitors)
  - **Observer** (watches dashboards, takes notes)
  - **Abort Authority** (can call off experiment if unsafe)
- [ ] **Define success criteria** (measurable, e.g., "error rate <5%")
- [ ] **Define abort criteria** (e.g., "error rate >10% for 2 min")
- [ ] **Announce in Slack** (`#gameday`, `#engineering`):
  ```
  📅 GameDay scheduled: 2025-11-06 14:00 UTC
  Scenario: Database Failover (Scenario 1)
  Impact: Possible brief error rate spike (<1 min), canary traffic only
  Contact: @alice (Chaos Operator), @bob (Abort Authority)
  ```
- [ ] **Test abort procedure**: Verify `dosctl chaos abort <id>` works in staging

---

### 4.2 During GameDay (T=0)

**T-10 min**:
- [ ] Final go/no-go check (all participants ready? stakeholders notified?)
- [ ] Verify abort command ready

**T=0 (Start)**:
- [ ] Inject failure (see scenario procedure)
- [ ] Start timer (track duration of impact)

**T+1 min → T+end**:
- [ ] Monitor dashboards (error rate, latency, circuit breaker status)
- [ ] Observer documents timeline (what happened when?)
- [ ] If abort criteria met → **ABORT** (no shame, safety first)

**T+end**:
- [ ] Verify auto-recovery (or manually restore)
- [ ] Check SLIs (did we breach SLO?)

---

### 4.3 Post-GameDay (T+1h)

- [ ] **Debrief** (30 min, all participants):
  - What worked well?
  - What surprised us?
  - What didn't work?
- [ ] **Document results**:
  - Use template below (Section 5)
  - Success/failure, observed metrics, action items
- [ ] **File action items** (Jira/Linear):
  - Fix bugs found (e.g., circuit breaker didn't open)
  - Update runbooks (add steps we had to improvise)
  - Improve observability (add missing dashboard panel)
- [ ] **Share learnings** (post in `#engineering`, present at All-Hands if major findings)

---

## 5. GameDay Report Template

**Template** (copy to new doc for each GameDay):

```markdown
# GameDay Report — <Scenario Name>

**Date**: 2025-11-06
**Duration**: 14:00-16:00 UTC (2 hours)
**Participants**: Alice (Chaos Operator), Bob (Observer), Charlie (Abort Authority)

---

## Scenario

**Objective**: Validate database failover

**Hypothesis**: "Failover completes in <30s, app auto-reconnects, <1% failed requests."

**Abort Criteria**: Error rate >5% for >2 min

---

## Results

**Outcome**: ✅ Success

**Metrics**:
- Failover duration: 22s (target: <30s) ✅
- Error rate during failover: 2.5% (target: <5%) ✅
- Manual intervention: None ✅
- Alerts: DatabasePrimaryDown fired + auto-resolved ✅

**Timeline**:
- 14:00:00 — Baseline metrics captured (availability: 99.95%)
- 14:00:30 — Injected failure (primary DB marked unhealthy)
- 14:00:35 — Alert fired: DatabasePrimaryDown (P1)
- 14:00:52 — Replica promoted to primary, app reconnected (22s total)
- 14:01:00 — Error rate returned to baseline
- 14:05:00 — Experiment ended, DB restored

---

## What Went Well

- Auto-failover worked as designed (no manual intervention)
- Alerts fired promptly and accurately
- Oncall runbook was clear (team knew not to intervene during drill)

---

## What Went Wrong

- Brief 2.5% error rate (higher than hoped, but acceptable)
- Dashboard didn't show replica promotion status (had to check kubectl manually)

---

## Action Items

- [ ] Add "replica promotion status" panel to DB dashboard (OPS-1234, Owner: Alice, Due: 2025-11-15)
- [ ] Investigate 2.5% errors (some clients may have stale connections?) (DEV-1235, Owner: Bob, Due: 2025-11-20)
- [ ] Schedule follow-up GameDay (Region Failover, Scenario 4) (OPS-1236, Owner: Charlie, Due: 2025-12-01)

---

## Lessons Learned

- Failover is robust, gives confidence for real incidents
- Observability gap: Need better visibility into DB cluster state
- Team is well-trained (no panic, followed runbook)

---

**Report Published**: https://wiki/gamedays/2025-11-06-db-failover
```

---

## 6. Advanced Scenarios (Future)

### Scenario 6: Data Corruption (Rollback + Restore)

**Objective**: Practice restoring from backup after data corruption.

**Steps**:
1. Inject: Corrupt small subset of data (test users only)
2. Detect: Monitoring catches integrity violation
3. Mitigate: Rollback app to last-known-good version, restore DB from backup
4. Verify: Checksums match, test users' data restored

**Risk**: High (involves data manipulation). Only run in dedicated staging env first.

---

### Scenario 7: Security Breach (Simulated Pen-Test)

**Objective**: Test incident response to unauthorized access.

**Steps**:
1. Red Team: Simulates attacker (gains access to non-prod account)
2. Detection: SIEM alerts on anomalous behavior
3. Response: Security oncall locks account, rotates credentials, investigates
4. Postmortem: How did attacker gain access? Patch vulnerability

**Frequency**: Annually (coordinated with Security team)

---

### Scenario 8: Compliance Audit Simulation

**Objective**: Practice pulling audit logs for regulator.

**Steps**:
1. Scenario: "Regulator requests all decision explanations for user X, date range Y"
2. Response: Use audit trail to extract data
3. Verify: Completeness (no missing records), format (meets regulatory standard)

**Outcome**: Confidence that audit trail is production-ready.

---

## 7. Chaos Engineering Best Practices

### 7.1 Start Small

**Progression**:
1. **Staging**: Run experiment in non-prod (safe, but not realistic)
2. **Canary**: Run in prod, 10% traffic (real users, limited blast radius)
3. **Full Prod**: Run in prod, 20%+ traffic (only after canary success)

**Example**: Database failover first tested in staging (weekly), then canary (monthly), then full prod (quarterly).

---

### 7.2 Automate Chaos (Steady-State)

**Goal**: Run small chaos experiments continuously (e.g., kill 1 random pod/day).

**Tools**:
- **Chaos Mesh**: Kubernetes-native chaos engineering
- **Gremlin**: SaaS chaos platform
- **Custom**: `cronjob` that runs `kubectl delete pod --random`

**Benefits**:
- Teams stay sharp (incidents are routine, not panic-inducing)
- System forced to be resilient (can't rely on manual fixes)

**Caution**: Start with low-impact failures (single pod), not databases.

---

### 7.3 Blameless Culture

**Key**: GameDay is for learning, not punishment.

**If experiment fails**:
- ❌ Wrong: "Bob's code caused the failure, Bob is bad."
- ✅ Right: "We found a gap in retry logic. Let's fix it. Great learning!"

**If someone makes mistake during GameDay**:
- Example: "Alice accidentally aborted experiment too early."
- Response: "No problem, we learned abort procedure works! Let's rerun tomorrow."

---

## 8. GameDay Calendar (2025 Q4)

| Date | Scenario | Type | Participants |
|------|----------|------|--------------|
| 2025-11-06 | Database Failover (Scenario 1) | Canary Chaos | SRE + Dev + DBA |
| 2025-11-13 | Tabletop: Multi-Region Outage | Tabletop | Oncall rotation |
| 2025-11-20 | Dependency Timeout (Scenario 2) | Canary Chaos | SRE + Dev (Auth) |
| 2025-12-04 | Traffic Spike (Scenario 3) | Full Chaos | SRE + Dev + Infra |
| 2025-12-11 | Tabletop: Security Breach | Tabletop | Oncall + Security |
| 2025-12-18 | Cascading Failure (Scenario 5) | Canary Chaos | SRE + Dev |

**Note**: Dates may shift (avoid conflicts with major releases, holidays).

---

## 9. References

- **Chaos Engineering Book** (Netflix): https://principlesofchaos.org/
- **Google SRE Book — Testing for Reliability**: https://sre.google/sre-book/testing-reliability/
- **Oncall Runbook**: [runbook_oncall.md](runbook_oncall.md) (procedures to practice)
- **SLI/SLO Catalog**: [sli_slo_catalog.md](docs/sli_slo_catalog.md) (targets to validate)

---

## 10. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-04 | SRE Team | Gate-T: Initial GameDay playbook with 5 chaos scenarios + tabletop guide |

---

**END OF DOCUMENT**

**Questions?** Ask in `#gameday` channel or contact SRE team lead.
