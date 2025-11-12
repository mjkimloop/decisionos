#!/bin/bash
# Pre-Gate Risk Signal Synthesis
# 프리게이트 신호 합성

set -e

echo "[PRE] Synthesizing signals for risk governor..."

# 신호 파일 디렉토리 생성
mkdir -p var/signals

# 간단한 신호 합성 (실제로는 여러 소스에서 수집)
# 여기서는 샘플 신호를 생성
cat > var/signals/current.json <<EOF
{
  "drift_z": 0.5,
  "anomaly_score": 0.1,
  "infra_p95_ms": 450,
  "error_rate": 0.01,
  "quota_denies": 5,
  "budget_level": "ok"
}
EOF

echo "[OK] Signals ready: var/signals/current.json"
