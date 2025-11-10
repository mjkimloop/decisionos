#!/usr/bin/env bash
set -euo pipefail

ROLLOUT_MODE=${ROLLOUT_MODE:-argo}
ROLLOUT_NAME=${ROLLOUT_NAME:-judge-api}
ROLLOUT_NAMESPACE=${ROLLOUT_NAMESPACE:-decisionos}

log() {
  echo "[abort][$ROLLOUT_MODE] $*"
}

python - <<'PY'
import os, sys
from apps.policy.pep import PEP

if not PEP().enforce("deploy:abort"):
    print("[rbac] deploy:abort denied", file=sys.stderr)
    sys.exit(3)
PY

python - <<'PY'
import os
from apps.experiment.stage_file import write_stage_atomic

stage_path = os.environ.get("STAGE_PATH", "var/rollout/desired_stage.txt")
write_stage_atomic("abort", stage_path)
print(f"[stage] abort requested for {stage_path}")
PY

case "$ROLLOUT_MODE" in
  argo)
    cmd=(kubectl argo rollouts abort "$ROLLOUT_NAME" -n "$ROLLOUT_NAMESPACE")
    ;;
  nginx)
    cmd=(kubectl rollout undo deployment/"$ROLLOUT_NAME" -n "$ROLLOUT_NAMESPACE")
    ;;
  *)
    echo "[abort] unsupported ROLLOUT_MODE=$ROLLOUT_MODE" >&2
    exit 1
    ;;
esac

log "executing: ${cmd[*]}"
"${cmd[@]}"
