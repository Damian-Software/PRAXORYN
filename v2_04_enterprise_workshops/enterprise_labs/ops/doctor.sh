#!/usr/bin/env bash
set -euo pipefail
printf 'OS: '; . /etc/os-release; printf '%s\n' "${PRETTY_NAME}"
for bin in python3 git curl systemctl journalctl; do
  if command -v "$bin" >/dev/null 2>&1; then printf 'OK %s\n' "$bin"; else printf 'MISSING %s\n' "$bin"; fi
done
printf 'Ports (local):\n'
ss -ltn 2>/dev/null | head -20 || true
printf 'GPU tool:\n'
if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; else printf 'not available\n'; fi
