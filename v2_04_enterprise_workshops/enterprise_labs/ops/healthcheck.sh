#!/usr/bin/env bash
set -euo pipefail
url="${LOCALAI_BASE_URL:-http://127.0.0.1:8080}"
case "$url" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) echo 'ERROR: only loopback URL allowed in this laboratory' >&2; exit 2;;
esac
status="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 8 "$url/v1/models")"
if [[ "$status" == 200 ]]; then
  echo 'OK models endpoint available'
else
  echo "ERROR: models endpoint returned HTTP $status" >&2
  exit 1
fi
