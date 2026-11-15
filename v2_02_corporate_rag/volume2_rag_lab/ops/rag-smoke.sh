#!/usr/bin/env bash
set -euo pipefail
: "${RAG_APP_KEY_FILE:?Set RAG_APP_KEY_FILE first}"
: "${RAG_API_URL:=http://127.0.0.1:8092}"
[[ "$RAG_API_URL" == "http://127.0.0.1:8092" ]] || { echo 'Only loopback API URL is allowed' >&2; exit 2; }
token="$(<"$RAG_APP_KEY_FILE")"
curl --fail-with-body --silent --show-error "$RAG_API_URL/healthz"
printf '\n'
curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $token" \
  --data '{"question":"What does the incident owner record?"}' \
  "$RAG_API_URL/v1/rag/answers"
printf '\n'
