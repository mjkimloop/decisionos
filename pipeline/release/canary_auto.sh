#!/usr/bin/env bash
set -euo pipefail

# RBAC: deploy:promote 또는 deploy:abort 필요
export DECISIONOS_ALLOW_SCOPES="${DECISIONOS_ALLOW_SCOPES:-deploy:promote,deploy:abort}"

python -m jobs.canary_auto_promote || exit $?
