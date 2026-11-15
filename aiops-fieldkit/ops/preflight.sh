#!/usr/bin/env bash
set -euo pipefail
printf 'OS: '; . /etc/os-release; echo "$PRETTY_NAME"
printf 'Architecture: '; uname -m
printf 'Python: '; python3 --version
printf 'Model API: '; curl --fail --silent --show-error --max-time 8 http://127.0.0.1:8080/v1/models | head -c 300 || true
printf '\nListening sockets:\n'; ss -ltn 2>/dev/null | head -15 || true
printf '\nGPU (if supported):\n'; command -v nvidia-smi >/dev/null && nvidia-smi -L || true
