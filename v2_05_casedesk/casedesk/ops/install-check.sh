#!/usr/bin/env bash
set -euo pipefail
printf 'OS: '; . /etc/os-release; echo "$PRETTY_NAME"
for cmd in php nginx mysql curl ss; do
  if command -v "$cmd" >/dev/null; then printf 'OK: %s\n' "$cmd"; else printf 'MISSING: %s\n' "$cmd"; fi
done
php -m | grep -Ei 'pdo_mysql|curl|mbstring' || true
nginx -t
systemctl list-timers --all | grep casedesk || true
curl -fsS -o /dev/null -w 'model HTTP=%{http_code}\n' http://127.0.0.1:8080/v1/models || true
