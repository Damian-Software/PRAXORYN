#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export LOCALAI_DB="${PWD}/state/workflow.sqlite3"
export LOCALAI_INBOX="${PWD}/inbox"
export LOCALAI_OUTBOX="${PWD}/outbox"
python3 app/workflow.py init
python3 app/workflow.py import inbox/demo.eml
python3 app/workflow.py import inbox/tickets.csv
python3 app/workflow.py run-once --offline
python3 app/workflow.py list
printf '%s\n' 'Review with: python3 app/workflow.py show 1'
printf '%s\n' 'Approve manually with a named operator; never auto-send.'
