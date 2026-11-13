#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
STATE="${1:-./private-state}"
python3 -m launchkit --state "$STATE" init
python3 -m launchkit --state "$STATE" submit --tenant example --kind invoice_check --payload examples/invoice.json --key invoice0001
python3 -m launchkit --state "$STATE" work-once --backend offline
python3 -m launchkit --state "$STATE" audit-check
printf '%s\n' 'Next: use show, approve and verify with your returned job ID.'
