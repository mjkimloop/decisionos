#!/bin/bash
# Gate: Burn-rate + Risk Governor
# 게이트 실행 (버른레이트 + 리스크)

set -e

echo "[GATE] Running burn-rate gate..."
python -m jobs.burnrate_gate

echo "[GATE] Running risk governor..."
python -m jobs.risk_decide_and_stage

echo "[OK] Gates passed"
