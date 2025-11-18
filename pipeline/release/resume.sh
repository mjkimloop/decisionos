#!/usr/bin/env bash
set -euo pipefail

FLAG="${DECISIONOS_FREEZE_FILE:-var/release/freeze.flag}"
if [[ -f "$FLAG" ]]; then
  rm -f "$FLAG"
  echo "[resume] freeze flag removed ($FLAG)"
else
  echo "[resume] no freeze flag ($FLAG)"
fi
