#!/usr/bin/env bash
set -euo pipefail
mkdir -p var/backups
cp -f var/audit_ledger.jsonl "var/backups/audit_ledger_$(date +%Y%m%d%H%M%S).jsonl" || true

