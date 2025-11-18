# Production Cutover Checklist (D-1)

**Target Date**: [YYYY-MM-DD]
**Target Time**: [HH:MM UTC]
**Environment**: Production
**Version**: v0.5.11v+

---

## Pre-Flight Checks (24 hours before)

### 1. Infrastructure Readiness

- [ ] **Readyz Endpoint**: All systems healthy (`/readyz` → `status=ok`)
  ```bash
  bash scripts/ci/check_readyz_blocking.sh
  # Expected: exit code 0
  ```

- [ ] **Evidence Integrity**: All evidence verified, tampered=false
  ```bash
  bash scripts/ci/validate_evidence_integrity.sh
  # Expected: ✓✓✓ EVIDENCE INTEGRITY: VALID ✓✓✓
  ```

- [ ] **DR Recovery Validated**: RTO ≤ 15m, RPO ≤ 1 file
  ```bash
  bash pipeline/dr/measure_recovery_time.sh
  # Expected: ✓✓✓ DR RECOVERY: PASS ✓✓✓
  ```

### 2. Security & Compliance

- [ ] **Key Rotation Status**: No keys expiring within 7 days
  ```bash
  python scripts/ops/check_key_rotation_countdown.py
  # Expected: ✓✓✓ All keys healthy ✓✓✓
  ```

- [ ] **Policy Signatures**: All policies signed and verified
  ```bash
  python scripts/policy/verify.py configs/policy/*.json
  # Expected: All signatures valid
  ```

- [ ] **PII Circuit Breaker**: Enabled and operational
  ```bash
  python -m jobs.pii_circuit_breaker_monitor --once
  # Expected: Circuit breaker state: enabled
  ```

### 3. Canary Configuration

- [ ] **Manual Promotion Enforced**: Auto-promotion DISABLED
  ```bash
  bash scripts/ops/configure_manual_promotion.sh --status
  # Expected: ✓ Status: MANUAL PROMOTION ENABLED
  ```

- [ ] **Canary Health**: 3+ green windows, burst ≤ 1.5x
  ```bash
  # Check latest evidence
  jq '.canary.windows[-3:] | map({pass, burst})' var/evidence/latest.json
  # Expected: All pass=true, burst ≤ 1.5
  ```

- [ ] **Rehearsal Completed**: 25% → 50% + abort drill passed
  ```bash
  bash pipeline/release/cutover_rehearsal.sh --steps "25,50" --abort-drill yes
  # Expected: ✓✓✓ ALL REHEARSALS PASSED ✓✓✓
  ```

### 4. Observability & Alerting

- [ ] **Ops Dashboard**: All health checks green
  ```bash
  python scripts/ops/show_cutover_dashboard.py
  # Expected: Go/No-Go: GO
  ```

- [ ] **Slack Alerts**: Configured and tested
  ```bash
  # Verify SLACK_WEBHOOK_URL is set
  echo $SLACK_WEBHOOK_URL
  # Send test alert
  ```

- [ ] **Monitoring Baselines**: P50/P99 latency documented
  ```bash
  # Document current baselines for rollback decision
  jq '.perf' var/evidence/latest.json > var/cutover/baselines-$(date +%Y%m%d).json
  ```

---

## Cutover Execution (D-Day)

### Phase 1: Pre-Cutover Validation (T-30min)

- [ ] **Final Health Check**: Run full checklist
  ```bash
  python scripts/ops/show_cutover_dashboard.py --json > var/cutover/pre-cutover-$(date +%Y%m%d-%H%M).json
  ```

- [ ] **Freeze Deployments**: No code changes during cutover window
- [ ] **Notify Stakeholders**: Send cutover start notification
- [ ] **War Room Ready**: On-call team standing by

### Phase 2: Canary Promotion (T+0)

- [ ] **Step 1: Promote to 10%**
  ```bash
  bash pipeline/release/canary_step.sh 10
  # Wait: 15 minutes
  # Validate: Check health metrics
  ```

- [ ] **Step 2: Promote to 25%**
  ```bash
  bash pipeline/release/canary_step.sh 25
  # Wait: 30 minutes
  # Validate: 3 consecutive green windows
  ```

- [ ] **Step 3: Promote to 50%**
  ```bash
  bash pipeline/release/canary_step.sh 50
  # Wait: 30 minutes
  # Validate: Burst ≤ 1.5x, P99 ≤ baseline + 10%
  ```

- [ ] **Step 4: Promote to 100%**
  ```bash
  bash pipeline/release/canary_step.sh 100
  # Wait: 60 minutes
  # Validate: All metrics within SLO
  ```

### Phase 3: Post-Cutover Validation (T+2h)

- [ ] **Smoke Tests**: Run E2E test suite
  ```bash
  pytest tests/e2e/ -v
  ```

- [ ] **Performance Validation**: Compare against baseline
  ```bash
  # P50/P99 within ±10% of baseline
  jq '.perf' var/evidence/latest.json
  ```

- [ ] **Error Rate Check**: Error rate < 0.1%
  ```bash
  # Check evidence for error metrics
  ```

- [ ] **Evidence Integrity**: Verify no tampering
  ```bash
  bash scripts/ci/validate_evidence_integrity.sh
  ```

---

## Rollback Procedures

### Trigger Conditions (Automatic Abort)

- Readyz status: `degraded` or `error`
- Canary burst ratio: > 1.5x
- P99 latency: > baseline + 20%
- Error rate: > 0.5%
- Evidence tampered: `true`

### Manual Rollback

```bash
# Immediate abort
bash pipeline/release/abort.sh --reason "manual-rollback-[REASON]"

# Verify abort state
cat var/rollout/desired_stage.txt
# Expected: abort

# Check rollback completed
bash scripts/ci/check_readyz_blocking.sh
# Expected: exit code 0 (systems recovered)
```

### Post-Rollback Actions

1. **Capture Evidence**:
   ```bash
   cp var/evidence/latest.json var/incidents/rollback-$(date +%Y%m%d-%H%M).json
   ```

2. **Notify Stakeholders**: Send rollback notification

3. **Incident Review**: Schedule post-mortem within 24h

---

## Go/No-Go Decision Template

### Decision Criteria

| Category | Criteria | Status | Notes |
|----------|----------|--------|-------|
| **Infrastructure** | Readyz healthy | ☐ GO / ☐ NO-GO | |
| **Infrastructure** | Evidence integrity | ☐ GO / ☐ NO-GO | |
| **Infrastructure** | DR recovery validated | ☐ GO / ☐ NO-GO | |
| **Security** | Keys healthy (7+ days) | ☐ GO / ☐ NO-GO | |
| **Security** | All policies signed | ☐ GO / ☐ NO-GO | |
| **Security** | PII breaker operational | ☐ GO / ☐ NO-GO | |
| **Canary** | Manual promotion enforced | ☐ GO / ☐ NO-GO | |
| **Canary** | 3+ green windows | ☐ GO / ☐ NO-GO | |
| **Canary** | Rehearsal passed | ☐ GO / ☐ NO-GO | |
| **Ops** | Dashboard all green | ☐ GO / ☐ NO-GO | |
| **Ops** | Alerts configured | ☐ GO / ☐ NO-GO | |
| **Ops** | Team ready | ☐ GO / ☐ NO-GO | |

### Final Decision

- [ ] **GO**: All criteria met, proceed with cutover
- [ ] **NO-GO**: One or more criteria failed, postpone cutover

**Decision Maker**: ___________________________
**Signature**: ___________________________
**Date/Time**: ___________________________

---

## Automated Checklist Runner

Run all pre-flight checks automatically:

```bash
bash scripts/ops/run_preflight_checks.sh --report var/cutover/preflight-$(date +%Y%m%d-%H%M).json
```

Expected output:
```
✓ Readyz endpoint: healthy
✓ Evidence integrity: valid
✓ DR recovery: PASS (RTO=12m, RPO=0)
✓ Key rotation: healthy (30+ days remaining)
✓ Policy signatures: all valid
✓ PII circuit breaker: enabled
✓ Manual promotion: enforced
✓ Canary health: 5 green windows, burst=0.8x
✓ Rehearsal: passed
✓ Ops dashboard: GO

========================================
  ✓✓✓ ALL PRE-FLIGHT CHECKS: PASS ✓✓✓
========================================
Go/No-Go: GO
```

---

## Contact Information

**Incident Commander**: [Name] - [Phone] - [Slack]
**Technical Lead**: [Name] - [Phone] - [Slack]
**Platform Team**: [Slack Channel: #platform-cutover]
**Security Team**: [Slack Channel: #security-oncall]
**On-Call Rotation**: [PagerDuty/OpsGenie Link]

---

## References

- [Cutover Rehearsal Script](../../pipeline/release/cutover_rehearsal.sh)
- [Readyz Blocking Check](../../scripts/ci/check_readyz_blocking.sh)
- [Evidence Validation](../../scripts/ci/validate_evidence_integrity.sh)
- [DR Recovery Measurement](../../pipeline/dr/measure_recovery_time.sh)
- [Key Rotation Countdown](../../scripts/ops/check_key_rotation_countdown.py)
- [Manual Promotion Config](../../scripts/ops/configure_manual_promotion.sh)
- [Ops Dashboard](../../scripts/ops/show_cutover_dashboard.py)
