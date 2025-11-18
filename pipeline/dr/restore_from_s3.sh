#!/usr/bin/env bash
set -euo pipefail

: "${DECISIONOS_DR_POLICY_PATH:=configs/dr/sample_policy.json}"
: "${DECISIONOS_DR_DEST:=var/evidence/restore}"

echo "[DR] mode=${DECISIONOS_S3_MODE:-stub} bucket=${DECISIONOS_S3_BUCKET:-decisionos-evidence} prefix=${DECISIONOS_S3_PREFIX:-evidence/} dest=${DECISIONOS_DR_DEST}"
python -m jobs.dr_restore
echo "[DR] done. see ${DECISIONOS_DR_REPORT_PATH:-var/dr/restore-report.json}"
