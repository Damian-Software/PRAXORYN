#!/usr/bin/env bash
set -euo pipefail
: "${LOCAL_AI_CLIENT_TOKEN:?Set a client token in the environment}"
: "${LOCAL_AI_MODEL:?Set the loaded model ID}"
: "${LOCAL_AI_IDEMPOTENCY_KEY:?Provide a unique idempotency key}"
BASE_URL="${LOCAL_AI_GATEWAY_URL:-http://127.0.0.1:8091}"
JSON="$(python3 -c 'import json,os;print(json.dumps({"model":os.environ["LOCAL_AI_MODEL"],"messages":[{"role":"user","content":"Reply with OK."}],"max_tokens":16,"stream":False}))')"
curl --fail-with-body --silent --show-error --max-time 80 \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${LOCAL_AI_CLIENT_TOKEN}" \
  -H "Idempotency-Key: ${LOCAL_AI_IDEMPOTENCY_KEY}" \
  --data "$JSON" "$BASE_URL/v1/chat/completions"
printf '\n'
