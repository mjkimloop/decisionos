#!/usr/bin/env bash
set -euo pipefail
mkdir -p var/log var/evidence
CSV="${1:-var/log/reqlog-chaos.csv}"
N="${N_SAMPLES:-500}"
ERR_RATIO="${ERR_RATIO:-0.08}"
P95_MS="${P95_MS:-1500}"

python - "$CSV" "$N" "$ERR_RATIO" "$P95_MS" <<'PY'
import random, sys
from datetime import datetime, timedelta, timezone

csv, n, err_ratio, p95 = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
start = datetime.now(timezone.utc) - timedelta(seconds=n // 10)
with open(csv, "w", encoding="utf-8") as fh:
    fh.write("ts,status,latency_ms\n")
    for i in range(n):
        ts = start + timedelta(milliseconds=50 * i)
        latency = random.randint(150, 600)
        if random.random() < 0.1:
            latency = random.randint(p95, p95 + 600)
        status = 200
        if random.random() < err_ratio:
            status = random.choice([500, 502, 429])
        fh.write(f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')},{status},{latency}\n")
print(f"[chaos] wrote {csv}")
PY

python -m apps.cli.dosctl.witness_perf --csv "$CSV" --out var/evidence/perf-chaos.json || true
echo "[chaos] perf-chaos.json generated"
