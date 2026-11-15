#!/usr/bin/env bash
set -euo pipefail
: "${LOCALAI_DB:=./state/workflow.sqlite3}"
python3 --version
python3 app/workflow.py --db "$LOCALAI_DB" doctor
python3 app/workflow.py --db "$LOCALAI_DB" stats
python3 app/workflow.py --db "$LOCALAI_DB" list --status failed
ss -ltn 2>/dev/null | grep -E '(:8080|:8091)' || true
