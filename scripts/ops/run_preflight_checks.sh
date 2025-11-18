#!/usr/bin/env bash
# Automated pre-flight checks for production cutover
#
# Runs all critical health checks and generates Go/No-Go decision report.
#
# Usage:
#   bash scripts/ops/run_preflight_checks.sh
#   bash scripts/ops/run_preflight_checks.sh --report var/cutover/preflight.json
#   bash scripts/ops/run_preflight_checks.sh --verbose
#
# Exit codes:
#   0: All checks passed (GO)
#   1: Some checks failed (NO-GO)
#   2: Critical error (unable to complete checks)

set -euo pipefail

REPORT_FILE=""
VERBOSE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --report) REPORT_FILE="$2"; shift 2 ;;
    --verbose) VERBOSE=1; shift ;;
    -v) VERBOSE=1; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { echo "[preflight] $*"; }
error() { echo "[preflight ERROR] $*" >&2; }
verbose() { [ $VERBOSE -eq 1 ] && echo "[preflight VERBOSE] $*" || true; }

log "========================================="
log "  PRE-FLIGHT CHECKS FOR CUTOVER"
log "  Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
log "========================================="

# Track check results
declare -a CHECKS_PASSED=()
declare -a CHECKS_FAILED=()
declare -a CHECK_DETAILS=()

# Helper: run check and record result
run_check() {
  local name="$1"
  local command="$2"
  local details="${3:-}"

  verbose "Running check: $name"
  verbose "  Command: $command"

  if eval "$command" >/dev/null 2>&1; then
    log "  ✓ $name"
    CHECKS_PASSED+=("$name")
    CHECK_DETAILS+=("$name|PASS|$details")
    return 0
  else
    error "  ✗ $name"
    CHECKS_FAILED+=("$name")
    CHECK_DETAILS+=("$name|FAIL|$details")
    return 1
  fi
}

# 1. Infrastructure Checks
log ""
log "--- Infrastructure Checks ---"

run_check \
  "Readyz endpoint healthy" \
  "bash scripts/ci/check_readyz_blocking.sh" \
  "All systems operational"

run_check \
  "Evidence integrity valid" \
  "bash scripts/ci/validate_evidence_integrity.sh" \
  "All evidence verified, tampered=false"

# DR recovery check (may take 2-5 minutes, skip in quick mode)
if [ "${SKIP_DR_CHECK:-0}" != "1" ]; then
  run_check \
    "DR recovery validated" \
    "bash pipeline/dr/measure_recovery_time.sh" \
    "RTO ≤ 15m, RPO ≤ 1 file"
else
  log "  ⊘ DR recovery check (skipped)"
fi

# 2. Security & Compliance Checks
log ""
log "--- Security & Compliance Checks ---"

run_check \
  "Key rotation healthy" \
  "python scripts/ops/check_key_rotation_countdown.py --warn-days 7 --critical-days 3" \
  "No keys expiring within 7 days"

run_check \
  "Policy signatures valid" \
  "python scripts/policy/verify.py configs/policy/*.json" \
  "All policies signed and verified"

run_check \
  "PII circuit breaker operational" \
  "python -m jobs.pii_circuit_breaker_monitor --once" \
  "Circuit breaker enabled"

# 3. Canary Configuration Checks
log ""
log "--- Canary Configuration Checks ---"

run_check \
  "Manual promotion enforced" \
  "bash scripts/ops/configure_manual_promotion.sh --status | grep -q 'MANUAL PROMOTION ENABLED'" \
  "Auto-promotion disabled"

# Check canary health (requires evidence)
if [ -f "var/evidence/latest.json" ]; then
  green_count=$(jq -r '.canary.windows | map(select(.pass == true)) | length' var/evidence/latest.json 2>/dev/null || echo 0)
  max_burst=$(jq -r '.canary.windows[-3:] | map(.burst // 0) | max' var/evidence/latest.json 2>/dev/null || echo 0)

  if [ "$green_count" -ge 3 ] && (( $(echo "$max_burst <= 1.5" | bc -l 2>/dev/null || echo 0) )); then
    log "  ✓ Canary health metrics"
    CHECKS_PASSED+=("Canary health metrics")
    CHECK_DETAILS+=("Canary health metrics|PASS|$green_count green windows, burst=${max_burst}x")
  else
    error "  ✗ Canary health metrics"
    CHECKS_FAILED+=("Canary health metrics")
    CHECK_DETAILS+=("Canary health metrics|FAIL|green=$green_count, burst=${max_burst}x")
  fi
else
  error "  ✗ Canary health metrics (evidence not found)"
  CHECKS_FAILED+=("Canary health metrics")
  CHECK_DETAILS+=("Canary health metrics|FAIL|Evidence file not found")
fi

# 4. Observability Checks
log ""
log "--- Observability Checks ---"

run_check \
  "Ops dashboard accessible" \
  "python scripts/ops/show_cutover_dashboard.py --json | jq -e '.go_no_go == \"GO\" or .go_no_go == \"PENDING\"'" \
  "Dashboard health checks operational"

# Check Slack webhook (optional)
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  log "  ✓ Slack alerts configured"
  CHECKS_PASSED+=("Slack alerts configured")
  CHECK_DETAILS+=("Slack alerts configured|PASS|Webhook URL set")
else
  log "  ⊘ Slack alerts configured (optional)"
fi

# Summary
log ""
log "========================================="
log "  CHECK SUMMARY"
log "  Passed: ${#CHECKS_PASSED[@]}"
log "  Failed: ${#CHECKS_FAILED[@]}"
log "========================================="

# Generate report
if [ -n "$REPORT_FILE" ]; then
  mkdir -p "$(dirname "$REPORT_FILE")"

  # Determine Go/No-Go
  if [ ${#CHECKS_FAILED[@]} -eq 0 ]; then
    GO_NO_GO="GO"
  else
    GO_NO_GO="NO-GO"
  fi

  # Build JSON report
  cat > "$REPORT_FILE" <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "go_no_go": "$GO_NO_GO",
  "summary": {
    "total": $((${#CHECKS_PASSED[@]} + ${#CHECKS_FAILED[@]})),
    "passed": ${#CHECKS_PASSED[@]},
    "failed": ${#CHECKS_FAILED[@]}
  },
  "checks": [
EOF

  # Add check details
  first=1
  for detail in "${CHECK_DETAILS[@]}"; do
    IFS='|' read -r name status message <<< "$detail"

    if [ $first -eq 0 ]; then
      echo "," >> "$REPORT_FILE"
    fi
    first=0

    cat >> "$REPORT_FILE" <<EOF2
    {
      "name": "$name",
      "status": "$status",
      "message": "$message"
    }
EOF2
  done

  cat >> "$REPORT_FILE" <<EOF
  ]
}
EOF

  log ""
  log "Report saved: $REPORT_FILE"
fi

# Final decision
log ""
if [ ${#CHECKS_FAILED[@]} -eq 0 ]; then
  log "========================================="
  log "  ✓✓✓ ALL PRE-FLIGHT CHECKS: PASS ✓✓✓"
  log "========================================="
  log "  Go/No-Go: GO"
  log ""
  log "Ready for production cutover."
  exit 0
else
  log "========================================="
  log "  ✗✗✗ PRE-FLIGHT CHECKS: FAILED ✗✗✗"
  log "========================================="
  log "  Go/No-Go: NO-GO"
  log ""
  log "Failed checks:"
  for check in "${CHECKS_FAILED[@]}"; do
    error "  - $check"
  done
  log ""
  log "Fix issues before proceeding with cutover."
  exit 1
fi
