#!/usr/bin/env bash
# Configure manual-only promotion mode for production cutover
#
# Disables auto-promotion and enforces manual approval for all canary steps.
# This is REQUIRED for production cutover to ensure controlled rollout.
#
# Usage:
#   bash scripts/ops/configure_manual_promotion.sh --enable
#   bash scripts/ops/configure_manual_promotion.sh --disable
#   bash scripts/ops/configure_manual_promotion.sh --status
#
# Environment variables set:
#   DECISIONOS_AUTOPROMOTE_ENABLE=0    Disable automatic promotion
#   DECISIONOS_AUTOPROMOTE=0           Legacy flag (also disabled)
#
# Exit codes:
#   0: Configuration successful
#   1: Invalid arguments
#   2: Configuration verification failed

set -euo pipefail

MODE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable)
      MODE="manual"
      shift
      ;;
    --disable)
      MODE="auto"
      shift
      ;;
    --status)
      MODE="status"
      shift
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Usage: $0 [--enable|--disable|--status]"
      exit 1
      ;;
  esac
done

if [ -z "$MODE" ]; then
  MODE="status"
fi

log() { echo "[manual-promotion] $*"; }
error() { echo "[manual-promotion ERROR] $*" >&2; }
warn() { echo "[manual-promotion WARN] $*"; }

# Configuration file paths
ENV_FILE=".env"
SYSTEMD_ENV="/etc/systemd/system/decisionos.service.d/override.conf"
CONFIG_MARKER="var/runtime/manual_promotion.flag"

log "========================================="
log "  MANUAL PROMOTION CONFIGURATION"
log "  Mode: $MODE"
log "========================================="

if [ "$MODE" = "status" ]; then
  log ""
  log "Current configuration:"
  log "  DECISIONOS_AUTOPROMOTE_ENABLE: ${DECISIONOS_AUTOPROMOTE_ENABLE:-not set}"
  log "  DECISIONOS_AUTOPROMOTE: ${DECISIONOS_AUTOPROMOTE:-not set}"

  # Check if marker file exists
  if [ -f "$CONFIG_MARKER" ]; then
    marker_mode=$(cat "$CONFIG_MARKER" 2>/dev/null || echo "unknown")
    log "  Config marker: $marker_mode (file: $CONFIG_MARKER)"
  else
    log "  Config marker: not found"
  fi

  # Determine actual mode
  if [ "${DECISIONOS_AUTOPROMOTE_ENABLE:-0}" = "1" ]; then
    log ""
    log "  ⚠ Status: AUTO-PROMOTION ENABLED"
    warn "  Production cutover should use manual promotion!"
  else
    log ""
    log "  ✓ Status: MANUAL PROMOTION ENABLED"
    log "  All canary steps require manual approval"
  fi

  exit 0
fi

if [ "$MODE" = "manual" ]; then
  log ""
  log "Enabling manual-only promotion mode..."

  # Update .env file if it exists
  if [ -f "$ENV_FILE" ]; then
    log "  Updating $ENV_FILE"

    # Remove old entries
    sed -i '/^DECISIONOS_AUTOPROMOTE_ENABLE=/d' "$ENV_FILE" 2>/dev/null || true
    sed -i '/^DECISIONOS_AUTOPROMOTE=/d' "$ENV_FILE" 2>/dev/null || true

    # Add new entries
    echo "DECISIONOS_AUTOPROMOTE_ENABLE=0" >> "$ENV_FILE"
    echo "DECISIONOS_AUTOPROMOTE=0" >> "$ENV_FILE"

    log "    ✓ Updated $ENV_FILE"
  else
    log "  Creating $ENV_FILE"
    cat > "$ENV_FILE" <<EOF
# Manual promotion mode (for production cutover)
DECISIONOS_AUTOPROMOTE_ENABLE=0
DECISIONOS_AUTOPROMOTE=0
EOF
    log "    ✓ Created $ENV_FILE"
  fi

  # Create marker file
  mkdir -p "$(dirname "$CONFIG_MARKER")"
  echo "manual" > "$CONFIG_MARKER"
  log "  ✓ Created marker: $CONFIG_MARKER"

  # Export for current session
  export DECISIONOS_AUTOPROMOTE_ENABLE=0
  export DECISIONOS_AUTOPROMOTE=0

  log ""
  log "========================================="
  log "  ✓ MANUAL PROMOTION MODE: ENABLED"
  log "========================================="
  log ""
  log "Next steps:"
  log "  1. Restart services to apply configuration:"
  log "     sudo systemctl restart decisionos"
  log ""
  log "  2. Verify configuration:"
  log "     bash scripts/ops/configure_manual_promotion.sh --status"
  log ""
  log "  3. Test promotion workflow:"
  log "     bash pipeline/release/canary_step.sh 25"
  log "     # (should NOT auto-promote, requires manual approval)"

elif [ "$MODE" = "auto" ]; then
  log ""
  log "Disabling manual-only promotion mode (enabling auto-promotion)..."

  warn "  ⚠ This will enable automatic promotion!"
  warn "  ⚠ Only do this AFTER production cutover is complete!"

  read -p "Are you sure? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    log "Cancelled"
    exit 0
  fi

  # Update .env file
  if [ -f "$ENV_FILE" ]; then
    log "  Updating $ENV_FILE"

    # Remove old entries
    sed -i '/^DECISIONOS_AUTOPROMOTE_ENABLE=/d' "$ENV_FILE" 2>/dev/null || true
    sed -i '/^DECISIONOS_AUTOPROMOTE=/d' "$ENV_FILE" 2>/dev/null || true

    # Add new entries
    echo "DECISIONOS_AUTOPROMOTE_ENABLE=1" >> "$ENV_FILE"
    echo "DECISIONOS_AUTOPROMOTE=1" >> "$ENV_FILE"

    log "    ✓ Updated $ENV_FILE"
  fi

  # Update marker file
  mkdir -p "$(dirname "$CONFIG_MARKER")"
  echo "auto" > "$CONFIG_MARKER"
  log "  ✓ Updated marker: $CONFIG_MARKER"

  # Export for current session
  export DECISIONOS_AUTOPROMOTE_ENABLE=1
  export DECISIONOS_AUTOPROMOTE=1

  log ""
  log "========================================="
  log "  ✓ AUTO-PROMOTION MODE: ENABLED"
  log "========================================="
  log ""
  log "Next steps:"
  log "  1. Restart services to apply configuration"
  log "  2. Verify configuration with --status"
fi

exit 0
