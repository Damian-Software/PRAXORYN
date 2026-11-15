# Local AI: review-first enterprise intake workflow

This project accompanies Volume II of "LOCAL AI", by Damián Zelený.
It uses Python's standard library and SQLite. No containers required.

## Offline quickstart

Run from this directory (Python 3.11+):

```bash
python3 app/workflow.py init
python3 app/workflow.py import inbox/demo.eml
python3 app/workflow.py import inbox/tickets.csv
python3 app/workflow.py run-once --offline
python3 app/workflow.py list
python3 app/workflow.py show 1
python3 app/workflow.py approve 1 --actor reviewer-01
python3 app/workflow.py export 1 --actor reviewer-01
```

Open `outbox/draft-1.eml` using a mail client. This tool NEVER sends emails.
`--offline` generates a deterministic synthetic draft for installation checks.
A normal `run-once` uses the existing OpenAI-compatible inference server at
`LOCALAI_API_URL` (loopback only), model `LOCALAI_MODEL`, and `LOCALAI_API_TOKEN`.

```bash
export LOCALAI_API_URL=http://127.0.0.1:8080
export LOCALAI_MODEL=YOUR_MODEL_ID
export LOCALAI_API_TOKEN=YOUR_SERVICE_TOKEN
python3 app/workflow.py run-once
```

Always verify `/v1/models` and one direct chat completion call before integrating.
The upstream HTTP contract is compatible with a subset of chat completions,
not every API or every provider.

## Design and limitations

- Only `.eml` `text/plain` and a strict `.csv` schema are supported.
- Import is limited to 64 KiB per file and each item is idempotent by hash.
- A database lease is claimed in `BEGIN IMMEDIATE`; the model request is
  made outside the transaction.
- Drafts require a *named* operator approval. No sending is automatic.
- No attachment processing, remote URL retrieval, inbound mail login, payment,
  CRM writeback, IAM, encrypted persistent content or multi-tenant ACL.
- The SQLite database contains raw message text. Use synthetic data only until
  encryption, retention and organizational access controls are implemented.
- Log only statuses, queue counts and error categories; avoid prompting text.
- Before production, change from local single-instance design to architecture
  reviewed for your concurrency, security, retention and legal obligations.

## Directory and file permissions

Use a dedicated non-privileged service account on Debian. Limit write access
for `state/`, `outbox/`, and the approved input directory. Avoid world-readable
environment files and never commit secrets into a repository.

## Operator diagnostics

```bash
python3 app/workflow.py doctor
python3 app/workflow.py stats
python3 app/workflow.py list --status failed
python3 -m unittest discover -s tests -v
```

For production, keep approval and export operations in a separate operator
context; do not give the automated worker access to arbitrary mail delivery.

## Development notes

The reference code is meant for inspection, not wholesale Internet exposure.
Do not expose it through a web server. Run it locally or behind a separate
identity provider, validated APIs and audited operators. Validate backups and
practice restore before accepting real documents.
