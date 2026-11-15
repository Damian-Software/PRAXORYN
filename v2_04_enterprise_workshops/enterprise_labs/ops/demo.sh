#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$(mktemp -d /tmp/localai-enterprise-demo.XXXXXX)"
python3 "$root/finance/invoices.py" "$root/samples/invoice_items.csv" --invoice-id DEMO001 --out "$out/documents"
python3 "$root/security/triage.py" "$root/samples/events.jsonl" --threshold 4 --out "$out/security-proposals.json"
python3 -m unittest discover -s "$root/tests" -q
printf 'Demo artifacts (synthetic only): %s\n' "$out"
