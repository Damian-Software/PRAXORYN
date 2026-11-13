#!/usr/bin/env bash
# Repeatable local-only smoke test. No network API or live model is called.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
HOME_DIR="${1:-$ROOT/demo-state}"
if [[ -e "$HOME_DIR" ]]; then
  echo "Destination exists; choose a fresh demo-state directory." >&2
  exit 2
fi
python3 -m praxoryn_studio --home "$HOME_DIR" init
JSON=$(python3 -m praxoryn_studio --home "$HOME_DIR" submit \
  --tenant demo_school --kind education \
  --prompt-file examples/studio/school.txt)
JOB_ID=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["job_id"])' <<<"$JSON")
python3 -m praxoryn_studio --home "$HOME_DIR" work-once
python3 -m praxoryn_studio --home "$HOME_DIR" show --tenant demo_school "$JOB_ID"
python3 -m praxoryn_studio --home "$HOME_DIR" approve \
  --tenant demo_school --reviewer reviewer01 "$JOB_ID"
python3 -m praxoryn_studio --home "$HOME_DIR" export --tenant demo_school "$JOB_ID"
unzip -t "$HOME_DIR/exports/$JOB_ID.zip"
echo "DONE: $JOB_ID"
