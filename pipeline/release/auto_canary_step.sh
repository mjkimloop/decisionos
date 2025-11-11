#!/bin/bash
# Auto Canary Step Adjustment Script
# drift severity에 따라 canary step 자동 조정
set -e

DRIFT_PATH="var/alerts/posterior_drift.json"
CANARY_CONFIG="configs/canary/policy.autotuned.json"

if [ ! -f "$DRIFT_PATH" ]; then
  echo "[INFO] No drift data, skip canary adjust"
  exit 0
fi

echo "[INFO] Running canary step adjust..."
python jobs/canary_step_adjust.py \
  --drift-path "$DRIFT_PATH" \
  --canary-config "$CANARY_CONFIG" \
  --out "$CANARY_CONFIG"

echo "[OK] Canary step adjusted"
