#!/usr/bin/env bash
# Evidence integrity validation for CI gates
#
# Validates:
#   1. index.json: tampered=false
#   2. All Evidence files contain required fields: judges, perf, perf_judge, canary
#   3. SHA256 checksums match between index and actual files
#
# Usage:
#   bash scripts/ci/validate_evidence_integrity.sh
#   bash scripts/ci/validate_evidence_integrity.sh --evidence-dir var/evidence
#
# Environment:
#   EVIDENCE_DIR                 Evidence directory (default: var/evidence)
#   DECISIONOS_EVIDENCE_STRICT   Strict mode (default: 1)
#
# Exit codes:
#   0: All evidence valid
#   1: Validation failed (BLOCKING)
#   2: Critical error (missing index, etc.)

set -euo pipefail

EVIDENCE_DIR="${EVIDENCE_DIR:-var/evidence}"
STRICT="${DECISIONOS_EVIDENCE_STRICT:-1}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    --lenient) STRICT=0; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { echo "[evidence-validate] $*"; }
error() { echo "[evidence-validate ERROR] $*" >&2; }
warn() { echo "[evidence-validate WARN] $*"; }

log "========================================="
log "  EVIDENCE INTEGRITY VALIDATION"
log "  Evidence dir: $EVIDENCE_DIR"
log "  Strict mode: $STRICT"
log "========================================="

# Check if evidence directory exists
if [ ! -d "$EVIDENCE_DIR" ]; then
  error "Evidence directory not found: $EVIDENCE_DIR"
  exit 2
fi

# Check if index.json exists
INDEX_FILE="$EVIDENCE_DIR/index.json"
if [ ! -f "$INDEX_FILE" ]; then
  error "Evidence index not found: $INDEX_FILE"
  exit 2
fi

log ""
log "--- Step 1: Validate index.json ---"

# Check tampered flag
tampered=$(jq -r '.tampered // "unknown"' "$INDEX_FILE")
log "  Tampered flag: $tampered"

if [ "$tampered" = "true" ]; then
  error "  ✗ Evidence has been tampered with (BLOCKING)"
  exit 1
elif [ "$tampered" = "unknown" ]; then
  warn "  ⚠ Tampered flag missing (treating as false)"
elif [ "$tampered" = "false" ]; then
  log "  ✓ Evidence integrity: OK"
else
  error "  ✗ Invalid tampered value: $tampered"
  exit 1
fi

# Check if index has entries
entry_count=$(jq -r '.entries | length' "$INDEX_FILE" 2>/dev/null || echo 0)
log "  Evidence entries: $entry_count"

if [ "$entry_count" -eq 0 ]; then
  warn "  ⚠ No evidence entries found"
  if [ "$STRICT" = "1" ]; then
    error "  ✗ Empty evidence in strict mode (BLOCKING)"
    exit 1
  fi
fi

log ""
log "--- Step 2: Validate required fields ---"

REQUIRED_FIELDS=("judges" "perf" "perf_judge" "canary")
failed=0

# Read entries and validate
entries=$(jq -c '.entries[]' "$INDEX_FILE" 2>/dev/null || echo "")

if [ -z "$entries" ]; then
  warn "  No entries to validate"
else
  while IFS= read -r entry; do
    file=$(echo "$entry" | jq -r '.file // "unknown"')
    sha256_index=$(echo "$entry" | jq -r '.sha256 // ""')

    log ""
    log "  Checking: $file"

    # Check if file exists
    evidence_file="$EVIDENCE_DIR/$file"
    if [ ! -f "$evidence_file" ]; then
      error "    ✗ File not found: $evidence_file"
      failed=1
      continue
    fi

    # Validate required fields in evidence file
    for field in "${REQUIRED_FIELDS[@]}"; do
      if ! jq -e ".$field" "$evidence_file" >/dev/null 2>&1; then
        error "    ✗ Missing required field: $field"
        failed=1
      else
        log "    ✓ Field present: $field"
      fi
    done

    # Validate SHA256 checksum
    if [ -n "$sha256_index" ]; then
      if command -v sha256sum >/dev/null 2>&1; then
        sha256_actual=$(sha256sum "$evidence_file" | awk '{print $1}')
      elif command -v shasum >/dev/null 2>&1; then
        sha256_actual=$(shasum -a 256 "$evidence_file" | awk '{print $1}')
      else
        warn "    ⚠ No SHA256 tool available (skipping checksum)"
        continue
      fi

      if [ "$sha256_actual" = "$sha256_index" ]; then
        log "    ✓ SHA256 match: ${sha256_actual:0:16}..."
      else
        error "    ✗ SHA256 mismatch:"
        error "      Index:  $sha256_index"
        error "      Actual: $sha256_actual"
        failed=1
      fi
    else
      warn "    ⚠ No SHA256 in index (skipping checksum)"
    fi

  done <<< "$entries"
fi

log ""
log "========================================="

if [ $failed -eq 0 ]; then
  log "  ✓✓✓ EVIDENCE INTEGRITY: VALID ✓✓✓"
  log "========================================="
  exit 0
else
  error "  ✗✗✗ EVIDENCE INTEGRITY: FAILED ✗✗✗"
  log "========================================="
  exit 1
fi
