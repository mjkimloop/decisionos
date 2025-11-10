#!/usr/bin/env bash
set -euo pipefail
SRC=${1:?usage: restore.sh <backup_file>}
cp -f "$SRC" var/audit_ledger.jsonl

