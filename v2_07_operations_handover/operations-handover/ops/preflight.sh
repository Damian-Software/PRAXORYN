#!/usr/bin/env bash
set -euo pipefail
# Read-only baseline. Do not print environment variables or tokens.
. /etc/os-release
printf 'OS: %s\n' "$PRETTY_NAME"
printf 'Kernel: '; uname -r
printf 'Python: '; python3 --version
printf 'Disk space:\n'; df -h / | tail -n 1
printf 'Service state (if installed):\n'; systemctl is-active praxops-probe.service 2>/dev/null || true
printf 'GPU (if visible):\n'; if command -v nvidia-smi >/dev/null; then nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; else echo unavailable; fi
printf 'Listening TCP ports:\n'; ss -ltn | sed -n '1,15p'
