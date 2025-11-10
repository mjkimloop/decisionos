#!/usr/bin/env bash
# scaffold: simple load test using curl
URL=${1:-http://localhost:8080/api/v1/decide/lead_triage}
for i in $(seq 1 10); do
  curl -s -X POST "$URL" -H 'Content-Type: application/json' -H 'X-Api-Key: dev-key' -d '{"org_id":"orgA","payload":{"credit_score":700,"dti":0.3,"income_verified":true}}' >/dev/null &
done
wait
echo "done"
