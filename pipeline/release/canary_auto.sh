#!/usr/bin/env bash
set -euo pipefail

# RBAC: deploy:promote �Ǵ� deploy:abort �ʿ�
export DECISIONOS_ALLOW_SCOPES="${DECISIONOS_ALLOW_SCOPES:-deploy:promote,deploy:abort}"

CHANGE_SERVICE="${CHANGE_SERVICE:-ops-api}"
python -m scripts.change.verify_freeze_window --service "$CHANGE_SERVICE" --labels "${CHANGE_LABELS:-}" || exit 2

python -m jobs.canary_auto_promote || exit $?
