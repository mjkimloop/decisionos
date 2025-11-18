#!/usr/bin/env bash
set -euo pipefail

FLAG="${DECISIONOS_FREEZE_FILE:-var/release/freeze.flag}"
mkdir -p "$(dirname "$FLAG")"
echo "freeze=$(date -u +"%Y-%m-%dT%H:%M:%SZ") reason=${1:-manual}" > "$FLAG"
echo "[pause] freeze flag created at $FLAG"
