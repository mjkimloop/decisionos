#!/bin/bash
# Post-Gate Alerts
# 포스트게이트 알림 및 PR 코멘트

set -e

echo "[POST] Running shadow autotune..."
python -m jobs.shadow_autotune

echo "[POST] Dispatching alerts..."
python -m apps.alerts.dispatcher --dry-run=false --level=info --reason=release:completed --message="Release gate completed successfully"

echo "[POST] Exporting metrics snapshot..."
python -c "from apps.ops.metrics import export_snapshot; export_snapshot('var/artifacts/metrics_snapshot.txt')"

echo "[OK] Post-gate complete"
