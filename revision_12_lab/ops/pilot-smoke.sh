#!/usr/bin/env bash
set -euo pipefail
: "${AI_CLIENT_TOKEN:?Set AI_CLIENT_TOKEN in the environment}"
url="${AI_PORTAL_URL:-http://127.0.0.1:8090/api/chat.php}"
response="$(curl --fail-with-body --silent --show-error --connect-timeout 3 --max-time 75 \
  -H "Authorization: Bearer ${AI_CLIENT_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data '{"prompt":"Reply with only OK"}' "$url")"
python3 -c 'import json,sys; result=json.loads(sys.stdin.read()); assert isinstance(result["answer"],str); assert result["request_id"]' <<< "$response"
echo 'PASS: authenticated request returned a structured answer'
unauth="$(curl -sS -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' --data '{"prompt":"test"}' "$url")"
test "$unauth" = 401
printf 'PASS: missing bearer token -> HTTP %s\n' "$unauth"
