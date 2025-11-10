#!/usr/bin/env bash
set -euo pipefail

STAGE_PATH="${STAGE_PATH:-var/rollout/desired_stage.txt}"
RBAC_SCOPE="${RBAC_SCOPE:-deploy:promote}"
HOOK_CMD="${DECISIONOS_CONTROLLER_HOOK:-}"

python - <<'PY'
import os, sys
from apps.policy.pep import PEP

scope = os.environ.get("RBAC_SCOPE", "deploy:promote")
if not PEP().enforce(scope):
    print(f"[promote] RBAC denied for scope '{scope}'", file=sys.stderr)
    sys.exit(3)
PY

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
