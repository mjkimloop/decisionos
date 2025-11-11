#!/usr/bin/env bash
set -euo pipefail
# 필요 환경변수: GH_APP_ID, GH_APP_PK (PK는 PEM 본문)
if [[ -z "${GH_APP_ID:-}" || -z "${GH_APP_PK:-}" ]]; then
  echo "GH App secrets missing; skip"; exit 0
fi
now=$(date +%s)
header='{"alg":"RS256","typ":"JWT"}'
payload=$(jq -nc --arg i "$GH_APP_ID" --arg n "$now" '{iat:($n|tonumber-60), exp:($n|tonumber+540), iss:($i|tonumber)}')
b64() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
unsigned="$(printf '%s' "$header" | b64).$(printf '%s' "$payload" | b64)"
sig=$(printf '%s' "$unsigned" | openssl dgst -sha256 -sign <(printf '%s' "$GH_APP_PK") -binary | b64)
jwt="$unsigned.$sig"

inst_id=$(curl -fsS -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" https://api.github.com/app/installations | jq '.[0].id')
if [[ -z "$inst_id" || "$inst_id" == "null" ]]; then echo "No installation"; exit 0; fi
token=$(curl -fsS -X POST -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" https://api.github.com/app/installations/$inst_id/access_tokens | jq -r '.token')
echo "$token"
