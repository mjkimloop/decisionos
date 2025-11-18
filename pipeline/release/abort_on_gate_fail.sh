#!/usr/bin/env bash
set -euo pipefail

SLO="${1:-configs/slo/slo-judge-infra.json}"
EVIDENCE="${2:-var/evidence/latest.json}"
PROVIDERS="${3:-var/providers-local.yaml}"
QUORUM="${4:-2/3}"

python - <<'PY'
import sys
from apps.policy.pep import require

try:
    require("deploy:abort")
except PermissionError:
    print("[rbac] deploy:abort denied", file=sys.stderr)
    sys.exit(3)
PY

echo "[abort-gate] running judge quorum (slo=$SLO, evidence=$EVIDENCE)"
set +e
python -m apps.cli.dosctl.judge_quorum \
  --slo "$SLO" \
  --evidence "$EVIDENCE" \
  --providers "$PROVIDERS" \
  --quorum "$QUORUM"
rc=$?
set -e

if [[ $rc -ne 0 ]]; then
  echo "[abort-gate] judge failed (rc=$rc) -> invoking abort.sh"
  cat var/gate/reasons.json 2>/dev/null | tr -d '\n' | sed 's/^/# reason=/' || true
  bash pipeline/release/abort.sh || true
  exit 2
fi

echo "[abort-gate] judge passed"
