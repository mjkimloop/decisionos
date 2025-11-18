#!/usr/bin/env bash
set -euo pipefail

STAGE_PATH="${STAGE_PATH:-var/rollout/desired_stage.txt}"
RBAC_SCOPE="${RBAC_SCOPE:-deploy:promote}"
HOOK_CMD="${DECISIONOS_CONTROLLER_HOOK:-}"

python - <<'PY'
import os, sys
from apps.policy.pep import require

scope = os.environ.get("RBAC_SCOPE", "deploy:promote")
try:
    require(scope)
except PermissionError:
    print(f"[promote] RBAC denied for scope '{scope}'", file=sys.stderr)
    sys.exit(3)
PY

CHANGE_SERVICE="${CHANGE_SERVICE:-ops-api}"
python -m scripts.change.verify_freeze_window --service "$CHANGE_SERVICE" --labels "${CHANGE_LABELS:-}" || exit 2
if [[ -n "${CAB_SIGNERS:-}" ]]; then
  python -m scripts.change.require_cab_multisig --service "$CHANGE_SERVICE" --signers "${CAB_SIGNERS}" || exit 2
fi
if [[ -n "${ONCALL_ACK_USERS:-}" ]]; then
  python -m scripts.change.require_oncall_ack --service "$CHANGE_SERVICE" --ack-users "${ONCALL_ACK_USERS}" || exit 2
fi
if [[ -n "${BREAK_GLASS_TOKEN:-}" ]]; then
  python -m scripts.change.break_glass verify --token "${BREAK_GLASS_TOKEN}" || exit 2
fi

python - <<'PY'
import os
from apps.experiment.stage_file import write_stage_atomic

stage_path = os.environ.get("STAGE_PATH", "var/rollout/desired_stage.txt")
write_stage_atomic("promote", stage_path)
print(f"[promote] stage token -> promote ({stage_path})")
PY

if [[ -n "${HOOK_CMD}" ]]; then
  echo "[promote] invoking hook: ${HOOK_CMD}"
  ${HOOK_CMD} || true
fi

echo "[promote] completed"
