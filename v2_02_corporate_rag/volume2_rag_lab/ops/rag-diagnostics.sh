#!/usr/bin/env bash
set -euo pipefail
printf 'Service status:\n'
systemctl is-active local-ai-rag.service || true
printf 'Listened ports:\n'
ss -ltn | grep -E ':(8080|8092|8093)[[:space:]]' || true
printf 'Database permissions:\n'
if [[ -e /var/lib/local-ai-rag/index.sqlite3 ]]; then
  stat -c '%a %U:%G %n' /var/lib/local-ai-rag/index.sqlite3
fi
printf 'Source directory permissions:\n'
if [[ -d /srv/local-ai-rag-docs ]]; then
  stat -c '%a %U:%G %n' /srv/local-ai-rag-docs
fi
# Do not print the environment file or the contents of secret files.
