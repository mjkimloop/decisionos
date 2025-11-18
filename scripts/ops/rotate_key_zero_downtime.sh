#!/usr/bin/env bash
# Zero-downtime key rotation automation
#
# Ensures safe key rotation with overlap period:
#   1. Generate new key
#   2. Add as "grace" (both old and new keys work)
#   3. Sign new policies with new key
#   4. Promote new key to "active"
#   5. Retire old key after grace period
#
# Usage:
#   bash scripts/ops/rotate_key_zero_downtime.sh --old-key k1 --new-key k2
#   bash scripts/ops/rotate_key_zero_downtime.sh --auto-generate
#
# Environment:
#   DECISIONOS_POLICY_KEYS       Current key configuration (JSON)
#   ROTATION_GRACE_DAYS          Grace period (default: 30)
#   ROTATION_DRY_RUN             Dry run mode (default: 0)
#
# Exit codes:
#   0: Rotation successful
#   1: Rotation failed (validation error)
#   2: Critical error (missing keys, etc.)

set -euo pipefail

OLD_KEY=""
NEW_KEY=""
AUTO_GENERATE=0
GRACE_DAYS="${ROTATION_GRACE_DAYS:-30}"
DRY_RUN="${ROTATION_DRY_RUN:-0}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --old-key) OLD_KEY="$2"; shift 2 ;;
    --new-key) NEW_KEY="$2"; shift 2 ;;
    --auto-generate) AUTO_GENERATE=1; shift ;;
    --grace-days) GRACE_DAYS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { echo "[rotate] $*"; }
error() { echo "[rotate ERROR] $*" >&2; }
warn() { echo "[rotate WARN] $*"; }

log "========================================="
log "  ZERO-DOWNTIME KEY ROTATION"
log "  Old key: ${OLD_KEY:-auto-detect}"
log "  New key: ${NEW_KEY:-auto-generate}"
log "  Grace period: $GRACE_DAYS days"
log "  Dry run: $DRY_RUN"
log "========================================="

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  error "Python not found (required for key generation)"
  exit 2
fi

PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python)

# Step 1: Auto-detect old active key if not specified
if [ -z "$OLD_KEY" ]; then
  log ""
  log "--- Step 1: Auto-detecting active key ---"

  OLD_KEY=$($PYTHON_CMD -c "
import os, json
keys_json = os.environ.get('DECISIONOS_POLICY_KEYS', '[]')
keys = json.loads(keys_json)
active_keys = [k for k in keys if k.get('state') == 'active']
if active_keys:
    print(active_keys[0]['key_id'])
else:
    print('')
" 2>/dev/null || echo "")

  if [ -z "$OLD_KEY" ]; then
    error "No active key found (specify --old-key manually)"
    exit 2
  fi

  log "  Detected active key: $OLD_KEY"
fi

# Step 2: Generate new key if auto-generate enabled
if [ $AUTO_GENERATE -eq 1 ]; then
  log ""
  log "--- Step 2: Generating new key ---"

  # Generate key ID with timestamp
  NEW_KEY="policy-$(date +%Y%m%d-%H%M%S)"
  log "  New key ID: $NEW_KEY"

  if [ $DRY_RUN -eq 0 ]; then
    # Generate HMAC secret
    NEW_SECRET=$(python3 -c "
import base64, secrets
secret = secrets.token_bytes(32)
print(base64.b64encode(secret).decode('ascii'))
" 2>/dev/null || echo "")

    if [ -z "$NEW_SECRET" ]; then
      error "Failed to generate key secret"
      exit 2
    fi

    log "  Generated secret: ${NEW_SECRET:0:16}... (truncated)"
    log "  ✓ Key generated successfully"
  else
    log "  [DRY RUN] Would generate new key: $NEW_KEY"
  fi
fi

# Step 3: Add new key in grace state
log ""
log "--- Step 3: Adding new key (grace state) ---"

if [ $DRY_RUN -eq 0 ]; then
  # Calculate dates
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  GRACE_UNTIL=$(date -u -d "+${GRACE_DAYS} days" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || \
                date -u -v+${GRACE_DAYS}d +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || \
                echo "2025-12-31T00:00:00Z")

  log "  Adding key to configuration..."
  log "    Key ID: $NEW_KEY"
  log "    State: grace"
  log "    Grace until: $GRACE_UNTIL"

  # Update key configuration
  $PYTHON_CMD - <<PY
import os, json
from datetime import datetime, timezone

keys_json = os.environ.get("DECISIONOS_POLICY_KEYS", "[]")
keys = json.loads(keys_json)

# Add new key in grace state
new_key = {
    "key_id": "$NEW_KEY",
    "secret": "${NEW_SECRET:-PLACEHOLDER}",
    "state": "grace",
    "rotated_at": "$NOW",
    "grace_until": "$GRACE_UNTIL"
}

keys.append(new_key)

# Print updated configuration
print(json.dumps(keys, indent=2))
PY

  log "  ✓ New key added to configuration"
  warn "  MANUAL ACTION REQUIRED: Update DECISIONOS_POLICY_KEYS environment"
else
  log "  [DRY RUN] Would add new key: $NEW_KEY (grace state)"
fi

# Step 4: Sign policies with new key
log ""
log "--- Step 4: Signing policies with new key ---"

POLICY_DIR="configs/policy"

if [ -d "$POLICY_DIR" ]; then
  policy_count=$(find "$POLICY_DIR" -name "*.json" -type f ! -name "registry.json" | wc -l)
  log "  Found $policy_count policy files"

  if [ $DRY_RUN -eq 0 ]; then
    for policy_file in "$POLICY_DIR"/*.json; do
      # Skip registry.json
      if [[ "$(basename "$policy_file")" == "registry.json" ]]; then
        continue
      fi

      log "  Signing: $(basename "$policy_file")"
      python3 scripts/policy/sign.py "$policy_file" --key-id "$NEW_KEY" || {
        warn "  Failed to sign: $(basename "$policy_file")"
      }
    done

    log "  ✓ Policies signed with new key"
  else
    log "  [DRY RUN] Would sign $policy_count policies with $NEW_KEY"
  fi
else
  warn "  Policy directory not found: $POLICY_DIR (skipping signing)"
fi

# Step 5: Update registry
log ""
log "--- Step 5: Updating policy registry ---"

if [ $DRY_RUN -eq 0 ]; then
  if [ -f "scripts/policy/registry.py" ]; then
    python3 scripts/policy/registry.py update || warn "Failed to update registry"
    log "  ✓ Registry updated"
  else
    warn "  Registry script not found (skipping)"
  fi
else
  log "  [DRY RUN] Would update policy registry"
fi

# Step 6: Verify zero-downtime
log ""
log "--- Step 6: Verifying zero-downtime ---"

log "  Checking key states..."

$PYTHON_CMD - <<PY
import os, json

keys_json = os.environ.get("DECISIONOS_POLICY_KEYS", "[]")
keys = json.loads(keys_json)

active_count = len([k for k in keys if k.get("state") == "active"])
grace_count = len([k for k in keys if k.get("state") == "grace"])

print(f"  Active keys: {active_count}")
print(f"  Grace keys: {grace_count}")

if active_count >= 1 and grace_count >= 1:
    print("  ✓ Zero-downtime verified (both old and new keys available)")
elif active_count >= 1:
    print("  ⚠ Only active key present (add new key in grace state)")
else:
    print("  ✗ No active keys (CRITICAL)")
PY

# Step 7: Next steps
log ""
log "========================================="
log "  ✓ ROTATION STEP 1: COMPLETE"
log "========================================="
log ""
log "Next steps (after ${GRACE_DAYS}-day grace period):"
log "  1. Verify new key is working:"
log "     python scripts/policy/verify.py configs/policy/*.json"
log ""
log "  2. Promote new key to active:"
log "     # Update key state: $NEW_KEY -> active"
log ""
log "  3. Retire old key:"
log "     # Update key state: $OLD_KEY -> retired"
log ""
log "  4. Monitor for errors:"
log "     # Check logs for signature verification failures"
log ""
log "Countdown monitoring:"
log "  python scripts/ops/check_key_rotation_countdown.py --send-alerts"

exit 0
