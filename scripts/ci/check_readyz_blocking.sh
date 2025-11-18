#!/usr/bin/env bash
# Readyz hard-gate enforcement for CI
#
# Usage:
#   bash scripts/ci/check_readyz_blocking.sh
#   bash scripts/ci/check_readyz_blocking.sh --url http://judge:8080/readyz
#
# Environment:
#   DECISIONOS_READYZ_FAIL_CLOSED=1   Hard-gate mode (required for production)
#   READYZ_URL                        Readyz endpoint (default: http://localhost:8080/readyz)
#   READYZ_TIMEOUT                    Timeout in seconds (default: 10)
#
# Exit codes:
#   0: Readyz healthy (status=ok)
#   1: Readyz degraded or error (BLOCKING)
#   2: Readyz endpoint unreachable (BLOCKING)

set -euo pipefail

READYZ_URL="${READYZ_URL:-http://localhost:8080/readyz}"
READYZ_TIMEOUT="${READYZ_TIMEOUT:-10}"
FAIL_CLOSED="${DECISIONOS_READYZ_FAIL_CLOSED:-1}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) READYZ_URL="$2"; shift 2 ;;
    --timeout) READYZ_TIMEOUT="$2"; shift 2 ;;
    --fail-open) FAIL_CLOSED=0; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { echo "[readyz-check] $*"; }
error() { echo "[readyz-check ERROR] $*" >&2; }

log "Checking readyz endpoint: $READYZ_URL"
log "  Timeout: ${READYZ_TIMEOUT}s"
log "  Fail-closed: $FAIL_CLOSED"

# Fetch readyz
response=$(curl -fsS --max-time "$READYZ_TIMEOUT" "$READYZ_URL" 2>/dev/null || echo '{"status":"error","error":"unreachable"}')

# Parse status
status=$(echo "$response" | jq -r '.status // "error"')

log "  Status: $status"

# Check status
case "$status" in
  ok)
    log "  ✓ Readyz: OK"
    echo "$response" | jq '.'
    exit 0
    ;;

  degraded|warning)
    if [ "$FAIL_CLOSED" = "1" ]; then
      error "  ✗ Readyz: $status (BLOCKING in fail-closed mode)"
      echo "$response" | jq '.'
      exit 1
    else
      log "  ⚠ Readyz: $status (allowed in fail-open mode)"
      echo "$response" | jq '.'
      exit 0
    fi
    ;;

  error|*)
    error "  ✗ Readyz: $status (BLOCKING)"
    echo "$response" | jq '.' || echo "$response"

    # Check required checks
    local failed_checks=$(echo "$response" | jq -r '.checks | to_entries | map(select(.value.status != "ok")) | length' 2>/dev/null || echo "unknown")
    if [ "$failed_checks" != "unknown" ] && [ "$failed_checks" -gt 0 ]; then
      error "  Failed checks: $failed_checks"
      echo "$response" | jq -r '.checks | to_entries | map(select(.value.status != "ok")) | .[] | "    - \(.key): \(.value.status)"' || true
    fi

    exit 2
    ;;
esac
