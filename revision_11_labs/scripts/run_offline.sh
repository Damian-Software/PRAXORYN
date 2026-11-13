#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 invoice_check.py fixtures/invoice_ok.json
python3 review_gate.py fixtures/code_checks_pass.json
python3 tenant_ledger.py
