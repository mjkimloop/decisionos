#!/usr/bin/env bash
set -euo pipefail
# Usage: chaos_inject.sh --errors=0.05 --latency-p95=1600 --judge-timeout=800
ERRORS=0.0
P95=0
JUDGE_TIMEOUT=0

for arg in "$@"; do
  case $arg in
    --errors=*) ERRORS="${arg#*=}"; shift ;;
    --latency-p95=*) P95="${arg#*=}"; shift ;;
    --judge-timeout=*) JUDGE_TIMEOUT="${arg#*=}"; shift ;;
  esac
done

echo "[chaos] injecting errors=$ERRORS p95=$P95 judge_timeout=$JUDGE_TIMEOUT"

# 샘플: reqlog에 지연/에러 샘플을 추가 (운영에선 트래픽 셰이퍼/프록시를 조작)
mkdir -p var/log
REQLOG="var/log/reqlog.csv"
echo "ts,status,latency_ms" > "$REQLOG"
python - <<PY
import random, time
from datetime import datetime, timezone
errors=float("$ERRORS"); p95=int("$P95")
for i in range(1000):
    ts=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    if random.random()<errors:
        status=500
    else:
        status=200
    base=100
    if p95>0 and random.random()<0.1:
        lat=p95+random.randint(50,200)
    else:
        lat=base+random.randint(0,100)
    print(f"{ts},{status},{lat}")
PY >> "$REQLOG"

# 저지 타임아웃 카오스(환경변수 플래그 등)
if [ "$JUDGE_TIMEOUT" -gt 0 ]; then
  export DECISIONOS_JUDGE_CHAOS_TIMEOUT_MS="$JUDGE_TIMEOUT"
fi

echo "[chaos] done"
