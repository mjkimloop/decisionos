#!/usr/bin/env bash
set -euo pipefail

ROLLOUT_MODE=${ROLLOUT_MODE:-argo}
ROLLOUT_NAME=${ROLLOUT_NAME:-judge-api}
ROLLOUT_NAMESPACE=${ROLLOUT_NAMESPACE:-decisionos}

log() {
  echo "[abort][$ROLLOUT_MODE] $*"
}

python - <<'PY'
import sys
from apps.policy.pep import require

try:
    require("deploy:abort")
except PermissionError:
    print("[rbac] deploy:abort denied", file=sys.stderr)
    sys.exit(3)
PY

CHANGE_SERVICE="${CHANGE_SERVICE:-ops-api}"
python -m scripts.change.verify_freeze_window --service "$CHANGE_SERVICE" --labels "${CHANGE_LABELS:-}" || exit 2
if [[ -n "${BREAK_GLASS_TOKEN:-}" ]]; then
  python -m scripts.change.break_glass verify --token "${BREAK_GLASS_TOKEN}" || exit 2
fi

python - <<'PY'
import os
from apps.experiment.stage_file import write_stage_atomic

stage_path = os.environ.get("STAGE_PATH", "var/rollout/desired_stage.txt")
write_stage_atomic("stable", stage_path)
print(f"[stage] stable requested for {stage_path}")
PY

case "$ROLLOUT_MODE" in
  argo)
    cmd=(kubectl argo rollouts abort "$ROLLOUT_NAME" -n "$ROLLOUT_NAMESPACE")
    ;;
  nginx)
    cmd=(kubectl rollout undo deployment/"$ROLLOUT_NAME" -n "$ROLLOUT_NAMESPACE")
    ;;
  none|noop)
    echo "[abort] ROLLOUT_MODE=$ROLLOUT_MODE → skipping external command"
    exit 0
    ;;
  *)
    echo "[abort] unsupported ROLLOUT_MODE=$ROLLOUT_MODE" >&2
    exit 1
    ;;
esac

log "executing: ${cmd[*]}"
"${cmd[@]}"
