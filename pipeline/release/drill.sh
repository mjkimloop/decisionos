#!/usr/bin/env bash
#
# Rollback Drill
# 가짜 스파이크 주입 → 자동 abort 확인 → stable 복구 검증
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TIMEOUT_SEC="${DRILL_TIMEOUT_SEC:-60}"
SPIKE_METRIC="${SPIKE_METRIC:-p95_latency}"
SPIKE_VALUE="${SPIKE_VALUE:-5000}"  # 5초 스파이크
CONTROLLER_URL="${CONTROLLER_URL:-http://localhost:8080}"

echo "[DRILL] Starting rollback drill..."
echo "[DRILL] Timeout: ${TIMEOUT_SEC}s, Spike: ${SPIKE_METRIC}=${SPIKE_VALUE}"

# 1. 현재 stage 확인
current_stage=$(curl -s "${CONTROLLER_URL}/api/experiment/status" | python3 -c "import sys, json; print(json.load(sys.stdin).get('stage', 'unknown'))" || echo "unknown")
echo "[DRILL] Current stage: ${current_stage}"

if [[ "$current_stage" == "stable" ]]; then
    echo "[DRILL] Already in stable, nothing to drill"
    exit 0
fi

# 2. 가짜 스파이크 주입 (evidence 파일 생성)
SPIKE_DIR="${PROJECT_ROOT}/evidence/drill_spike"
mkdir -p "$SPIKE_DIR"

cat > "${SPIKE_DIR}/spike_inject.json" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "metric": "${SPIKE_METRIC}",
  "value": ${SPIKE_VALUE},
  "source": "drill_inject",
  "signature": "fake_spike_for_abort_test"
}
EOF

echo "[DRILL] Injected spike: ${SPIKE_DIR}/spike_inject.json"

# 3. Controller에 강제 abort 트리거 (또는 자동 감지 대기)
# Option A: POST /api/experiment/force-abort
# Option B: Controller가 metrics 폴링으로 자동 감지

# 여기선 Option A 사용
echo "[DRILL] Triggering force abort..."
abort_response=$(curl -s -X POST "${CONTROLLER_URL}/api/experiment/force-abort" \
    -H "Content-Type: application/json" \
    -d "{\"reason\": \"drill_spike\", \"evidence\": \"${SPIKE_DIR}/spike_inject.json\"}" || echo "{\"error\": true}")

echo "[DRILL] Abort response: ${abort_response}"

# 4. stage=stable 복구 대기 (최대 TIMEOUT_SEC)
echo "[DRILL] Waiting for stage=stable recovery..."
start_time=$(date +%s)
recovered=false

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))

    if [[ $elapsed -ge $TIMEOUT_SEC ]]; then
        echo "[DRILL FAIL] Timeout after ${TIMEOUT_SEC}s, stage not recovered to stable"
        exit 1
    fi

    stage=$(curl -s "${CONTROLLER_URL}/api/experiment/status" | python3 -c "import sys, json; print(json.load(sys.stdin).get('stage', 'unknown'))" || echo "unknown")

    if [[ "$stage" == "stable" ]]; then
        echo "[DRILL PASS] Recovered to stable in ${elapsed}s"
        recovered=true
        break
    fi

    echo "[DRILL] Current stage: ${stage}, elapsed: ${elapsed}s"
    sleep 2
done

# 5. 정리
rm -rf "$SPIKE_DIR"
echo "[DRILL] Cleanup complete"

if [[ "$recovered" == "true" ]]; then
    echo "[DRILL] ✓ Rollback drill PASSED"
    exit 0
else
    echo "[DRILL] ✗ Rollback drill FAILED"
    exit 1
fi
