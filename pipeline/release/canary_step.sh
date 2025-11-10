#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: pipeline/release/canary_step.sh <stage_percent>

환경 변수:
  REQLOG_PATH            reqlog CSV 경로 (기본: var/log/reqlog.csv)
  JUDGELOG_PATH          judge reqlog CSV 경로 (기본: var/log/judgelog.csv)
  EVIDENCE_PATH          Evidence JSON (기본: var/evidence/latest.json)
  PROVIDERS_PATH         providers.yaml (기본: configs/judge/providers.yaml)
  SLO_INFRA_PATH         infra SLO JSON (기본: configs/slo/slo-judge-infra.json)
  SLO_CANARY_PATH        canary SLO JSON (기본: configs/slo/slo-canary.json)
  SHADOW_DIR             shadow capture 출력 디렉터리 (기본: var/shadow)
  PERF_JSON              reqlog → perf JSON 경로 (기본: var/evidence/perf-latest.json)
  JUDGE_PERF_JSON        judgelog → perf_judge JSON 경로 (기본: var/evidence/perf-judge-latest.json)
  CANARY_JSON            canary 비교 JSON (기본: var/evidence/canary-latest.json)
USAGE
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

STAGE="$1"

log() {
  echo "[canary-step][stage=${STAGE}] $*"
}

python - <<'PY'
import sys
from apps.policy.pep import PEP

if not PEP().enforce("deploy:canary"):
    print("[rbac] deploy:canary denied", file=sys.stderr)
    sys.exit(3)
PY

REQLOG_PATH=${REQLOG_PATH:-var/log/reqlog.csv}
JUDGELOG_PATH=${JUDGELOG_PATH:-var/log/judgelog.csv}
EVIDENCE_PATH=${EVIDENCE_PATH:-var/evidence/latest.json}
PROVIDERS_PATH=${PROVIDERS_PATH:-configs/judge/providers.yaml}
SLO_INFRA_PATH=${SLO_INFRA_PATH:-configs/slo/slo-judge-infra.json}
SLO_CANARY_PATH=${SLO_CANARY_PATH:-configs/slo/slo-canary.json}
SHADOW_DIR=${SHADOW_DIR:-var/shadow}
PERF_JSON=${PERF_JSON:-var/evidence/perf-latest.json}
JUDGE_PERF_JSON=${JUDGE_PERF_JSON:-var/evidence/perf-judge-latest.json}
CANARY_JSON=${CANARY_JSON:-var/evidence/canary-latest.json}

mkdir -p "$(dirname "$EVIDENCE_PATH")" "$(dirname "$PERF_JSON")" "$(dirname "$JUDGE_PERF_JSON")" "$SHADOW_DIR" var/rollout

python - <<'PY'
import os
from apps.experiment.stage_file import write_stage_atomic

stage_path = os.environ.get("STAGE_PATH", "var/rollout/desired_stage.txt")
write_stage_atomic("canary", stage_path)
print(f"[stage] state=canary path={stage_path}")
PY

log "capturing shadow traffic"
python -m apps.cli.dosctl.shadow_capture --out "$SHADOW_DIR" --samples "${SHADOW_SAMPLES:-20000}"
log "comparing canary vs control"
python -m apps.cli.dosctl.canary_compare \
  --control "$SHADOW_DIR/control.csv" \
  --canary "$SHADOW_DIR/canary.csv" \
  --out "$CANARY_JSON"

log "harvesting reqlog → perf"
python jobs/evidence_harvest_reqlog.py \
  --reqlog "$REQLOG_PATH" \
  --out-json "$PERF_JSON" \
  --evidence "$EVIDENCE_PATH"

log "harvesting judgelog → perf_judge + canary"
python jobs/evidence_harvest_judgelog.py \
  --judgelog "$JUDGELOG_PATH" \
  --out-json "$JUDGE_PERF_JSON" \
  --evidence "$EVIDENCE_PATH" \
  --canary-json "$CANARY_JSON"

log "running judge infra gate"
python -m apps.cli.dosctl.judge_quorum \
  --slo "$SLO_INFRA_PATH" \
  --evidence "$EVIDENCE_PATH" \
  --providers "$PROVIDERS_PATH" \
  --quorum "${QUORUM_EXPR:-2/3}" || exit 2

log "running canary gate"
python -m apps.cli.dosctl.judge_quorum \
  --slo "$SLO_CANARY_PATH" \
  --evidence "$EVIDENCE_PATH" \
  --providers "$PROVIDERS_PATH" \
  --quorum "${QUORUM_EXPR:-2/3}" || exit 2

log "stage ${STAGE}% validated"
