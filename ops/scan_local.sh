#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then echo "Usage: $0 /path/to/project [reports-dir]" >&2; exit 2; fi
root="$(realpath "$1")"
out="${2:-$PWD/reports}"
PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" \
  python3 -m codeops.cli scan --project "$root" --output "$out" --ci
