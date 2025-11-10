#!/usr/bin/env bash
set -euo pipefail
# 게이트 실패 시 stage=stable 원자 롤백
echo "[abort] release gate failed. rolling back to stable..."
python - <<'PY'
import os
from apps.experiment.stage_file import write_stage_atomic

stage_path = os.environ.get("STAGE_PATH", "var/rollout/desired_stage.txt")
write_stage_atomic("stable", stage_path)
print("[abort] stage=stable written")
PY
# TODO: Slack/Email webhook 자리
exit 1
