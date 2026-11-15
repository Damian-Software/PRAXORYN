#!/usr/bin/env bash
set -euo pipefail
repo="${1:?Specify a new scratch repository path}"
[[ ! -e "$repo" ]] || { printf 'ERROR: destination already exists\n' >&2; exit 2; }
mkdir -p "$repo"
git init -q -b main "$repo"
cat > "$repo/calculator.py" <<'PY'
def divide(a, b):
    if b == 0:
        raise ValueError('division by zero')
    return a / b
PY
git -C "$repo" add calculator.py
git -C "$repo" -c user.name=Demo -c user.email=demo@example.invalid commit -qm 'Start'
git -C "$repo" switch -qc feature/remove-validation
cat > "$repo/calculator.py" <<'PY'
def divide(a, b):
    return a / b
PY
git -C "$repo" add calculator.py
git -C "$repo" -c user.name=Demo -c user.email=demo@example.invalid commit -qm 'Add regression'
printf 'Demo ready: %s\n' "$repo"
