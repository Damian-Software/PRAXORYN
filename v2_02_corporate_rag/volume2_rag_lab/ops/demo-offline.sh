#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
python3 app/rag_cli.py --db "$work/index.db" --source-root fixtures/docs ingest incident.md
python3 app/rag_cli.py --db "$work/index.db" --source-root fixtures/docs ingest retention.txt
python3 app/rag_cli.py --db "$work/index.db" --source-root fixtures/docs search 'incident owner'
python3 app/rag_cli.py --db "$work/index.db" --source-root fixtures/docs stats
python3 app/rag_cli.py --db "$work/index.db" --source-root fixtures/docs check
