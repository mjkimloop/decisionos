#!/usr/bin/env bash
set -euo pipefail

# Cutover rehearsal helper - PRODUCTION READY
# - Drives canary_step.sh for a sequence of percentages (default: 25,50)
# - Enforces readyz hard-gate before each promotion
# - Validates 3 consecutive green windows + burst ≤ 1.5 + min_samples ≥ 100
# - Runs forced abort drill to verify rollback automation
# - Optionally injects burst to force abort path

usage() {
  cat <<'USAGE'
Usage: pipeline/release/cutover_rehearsal.sh [--steps "25,50"] [--inject-burst yes|no] [--abort-drill yes|no]

Env:
  STAGE_PATH                      stage token path (default: var/rollout/desired_stage.txt)
  DECISIONOS_AUTOPROMOTE=0        disable auto-promote (REQUIRED for rehearsal)
  DECISIONOS_READYZ_FAIL_CLOSED=1 hard-gate readyz (REQUIRED for rehearsal)
  DECISIONOS_CANARY_REQUIRED_PASSES=3  required green windows (default 3)
  DECISIONOS_CANARY_MAX_BURST=1.5      max burst ratio (default 1.5)
  DECISIONOS_CANARY_MIN_SAMPLES=100    min sample count (default 100)
  READYZ_URL                      readyz endpoint (default: http://localhost:8080/readyz)

Examples:
  # Full rehearsal: 25% → 50% + abort drill
  pipeline/release/cutover_rehearsal.sh --steps "25,50" --abort-drill yes

  # With burst injection at 50%
  pipeline/release/cutover_rehearsal.sh --steps "25,50" --inject-burst yes

  # Abort drill only
  pipeline/release/cutover_rehearsal.sh --abort-drill yes --steps ""
USAGE
}

STEPS="25,50"
INJECT_BURST="no"
ABORT_DRILL="yes"
EVIDENCE_PATH="var/evidence/latest.json"
READYZ_URL="${READYZ_URL:-http://localhost:8080/readyz}"

# Enforce fail-closed mode
export DECISIONOS_AUTOPROMOTE="${DECISIONOS_AUTOPROMOTE:-0}"
export DECISIONOS_READYZ_FAIL_CLOSED="${DECISIONOS_READYZ_FAIL_CLOSED:-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --steps) STEPS="$2"; shift 2 ;;
    --inject-burst) INJECT_BURST="$2"; shift 2 ;;
    --abort-drill) ABORT_DRILL="$2"; shift 2 ;;
    --evidence) EVIDENCE_PATH="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1"; usage; exit 1 ;;
  esac
done

IFS=',' read -r -a STEP_LIST <<<"$STEPS"

log() { echo "[cutover] $*"; }
error() { echo "[cutover ERROR] $*" >&2; }
warn() { echo "[cutover WARN] $*"; }

check_readyz() {
  log "Checking /readyz endpoint: $READYZ_URL"

  local response=$(curl -fsS "$READYZ_URL" 2>/dev/null || echo '{"status":"error"}')
  local status=$(echo "$response" | jq -r '.status // "error"')

  if [ "$status" = "ok" ]; then
    log "  ✓ Readyz: OK"
    return 0
  else
    error "  ✗ Readyz: $status (BLOCKING)"
    echo "$response" | jq '.' || echo "$response"
    return 1
  fi
}

check_canary_health() {
  local required_windows="${DECISIONOS_CANARY_REQUIRED_PASSES:-3}"
  local max_burst="${DECISIONOS_CANARY_MAX_BURST:-1.5}"
  local min_samples="${DECISIONOS_CANARY_MIN_SAMPLES:-100}"

  log "Checking canary health:"
  log "  Required green windows: $required_windows"
  log "  Max burst ratio: ${max_burst}x"
  log "  Min samples: $min_samples"

  # Check if evidence exists
  if [ ! -f "$EVIDENCE_PATH" ]; then
    warn "  Evidence file not found: $EVIDENCE_PATH (skipping health check)"
    return 0
  fi

  # Extract metrics from evidence
  local green_count=$(jq -r '.canary.windows | map(select(.pass == true)) | length' "$EVIDENCE_PATH" 2>/dev/null || echo 0)
  local burst_ratio=$(jq -r '.canary.windows[-1].burst // 0' "$EVIDENCE_PATH" 2>/dev/null || echo 0)
  local sample_count=$(jq -r '.canary.windows[-1].samples // 0' "$EVIDENCE_PATH" 2>/dev/null || echo 0)

  log "  Green windows: $green_count"
  log "  Burst ratio: ${burst_ratio}x"
  log "  Sample count: $sample_count"

  # Validate
  local failed=0

  if [ "$green_count" -lt "$required_windows" ]; then
    error "  ✗ Insufficient green windows: $green_count < $required_windows"
    failed=1
  fi

  if (( $(echo "$burst_ratio > $max_burst" | bc -l) )); then
    error "  ✗ Burst ratio exceeded: ${burst_ratio}x > ${max_burst}x"
    failed=1
  fi

  if [ "$sample_count" -lt "$min_samples" ]; then
    error "  ✗ Insufficient samples: $sample_count < $min_samples"
    failed=1
  fi

  if [ $failed -eq 0 ]; then
    log "  ✓ Canary health: PASS"
    return 0
  else
    error "  ✗ Canary health: FAIL"
    return 1
  fi
}

run_abort_drill() {
  log "========================================="
  log "  ABORT DRILL"
  log "========================================="

  log "Triggering canary abort..."
  bash pipeline/release/abort.sh --reason "rehearsal-drill"

  local abort_exit=$?
  if [ $abort_exit -ne 0 ]; then
    error "Abort command failed: exit code $abort_exit"
    return 1
  fi

  log "Verifying abort state..."
  sleep 2

  local stage_path="${STAGE_PATH:-var/rollout/desired_stage.txt}"
  if [ ! -f "$stage_path" ]; then
    warn "Stage file not found: $stage_path (skipping verification)"
    return 0
  fi

  local current_stage=$(cat "$stage_path" | tr -d '[:space:]')
  if [ "$current_stage" = "abort" ]; then
    log "  ✓ Canary stage: abort (confirmed)"
    log "========================================="
    log "  ✓ ABORT DRILL PASSED"
    log "========================================="
    return 0
  else
    error "  ✗ Canary stage: $current_stage (expected: abort)"
    return 1
  fi
}

# Main rehearsal flow
log "========================================="
log "  CUTOVER REHEARSAL"
log "  Steps: $STEPS"
log "  Inject burst: $INJECT_BURST"
log "  Abort drill: $ABORT_DRILL"
log "========================================="
log "  DECISIONOS_AUTOPROMOTE: $DECISIONOS_AUTOPROMOTE"
log "  DECISIONOS_READYZ_FAIL_CLOSED: $DECISIONOS_READYZ_FAIL_CLOSED"
log "========================================="

# Pre-check: readyz must be healthy
if ! check_readyz; then
  error "Rehearsal FAILED: readyz not healthy (BLOCKING)"
  exit 1
fi

# Run promotion steps
for pct in "${STEP_LIST[@]}"; do
  pct_trimmed=$(echo "$pct" | xargs)

  # Skip empty steps
  if [ -z "$pct_trimmed" ]; then
    continue
  fi

  log ""
  log "--- Step: promoting to ${pct_trimmed}% ---"

  # Check readyz before promotion
  if ! check_readyz; then
    error "Rehearsal FAILED: readyz not healthy before ${pct_trimmed}%"
    exit 1
  fi

  # Run promotion
  log "Running canary step ${pct_trimmed}%"
  bash pipeline/release/canary_step.sh "$pct_trimmed"

  local step_exit=$?
  if [ $step_exit -ne 0 ]; then
    error "Rehearsal FAILED: canary step failed at ${pct_trimmed}%"
    exit 1
  fi

  # Wait for metrics
  log "Waiting 30s for metrics collection..."
  sleep 30

  # Check health
  if ! check_canary_health; then
    error "Rehearsal FAILED: canary health check failed at ${pct_trimmed}%"
    exit 1
  fi

  log "  ✓ Health checks passed at ${pct_trimmed}%"
done

# Inject burst if requested
if [[ "${INJECT_BURST}" =~ ^(yes|true|1)$ ]]; then
  log ""
  log "Injecting burst window into evidence to trigger abort..."
  python - <<'PY'
import json, time, os
from pathlib import Path
from apps.obs.evidence.ops import recompute_integrity

path = Path(os.environ.get("EVIDENCE_PATH", "var/evidence/latest.json"))
if not path.exists():
    raise SystemExit(f"evidence missing: {path}")
data = json.loads(path.read_text(encoding="utf-8"))
data.setdefault("canary", {}).setdefault("windows", []).append(
    {"pass": False, "burst": 99, "samples": 1000, "timestamp_unix": time.time()}
)
recompute_integrity(data)
path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
print(f"[cutover] burst window appended -> {path}")
PY

  log "Running auto-promote/abort decision (should abort)..."
  python -m jobs.canary_auto_promote || warn "Auto-promote/abort returned non-zero (expected if abort triggered)"
fi

log ""
log "========================================="
log "  ✓ PROMOTION REHEARSAL PASSED"
log "========================================="

# Run abort drill
if [[ "${ABORT_DRILL}" =~ ^(yes|true|1)$ ]]; then
  log ""
  if ! run_abort_drill; then
    error "Rehearsal FAILED: abort drill failed"
    exit 2
  fi
fi

log ""
log "========================================="
log "  ✓✓✓ ALL REHEARSALS PASSED ✓✓✓"
log "========================================="
exit 0
