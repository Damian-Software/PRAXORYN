# AI Operations Field Kit — practical offline laboratory

This package extends the book's **Volume II**, chapter 453 onward. It is a reference implementation for training and controlled internal experiments. It is **not** a certified public multi-tenant API service.

## Quick start on Debian 13

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip curl sqlite3
cd aiops-fieldkit
python3 -m venv .venv
source .venv/bin/activate
python -m unittest discover -s tests -v
umask 077
python -m aiops init
python -m aiops tenant org-alpha --credit 5
python -m aiops submit org-alpha summary support_request.txt --workspace ./examples --key request-000001
python -m aiops work --mock
python -m aiops job org-alpha 1
python -m aiops review org-alpha 1 approve --actor reviewer@example.invalid
python -m aiops export org-alpha ./out/approved.html
python -m aiops finance ./examples/invoice_lines.csv
python -m aiops codecheck ./examples/unsafe_sample.py
python -m aiops guard ./examples/access.jsonl --threshold 4
```

The `--mock` switch is a deterministic simulation, not a model invocation. To use a real **existing local model API**:

```bash
export AI_BASE_URL=http://127.0.0.1:8080
export AI_MODEL=YOUR_MODEL_ID
# Optional: export AI_API_KEY=YOUR_SERVICE_TOKEN
python -m aiops submit org-alpha reply support_request.txt --workspace ./examples --key request-000002
python -m aiops work
```

Do not place tokens in source control or paste secret values into the book. The example does not include an HTTP authentication layer. The CLI operator is trusted and must run as a restricted service account. It is not safe to expose to untrusted users over SSH or HTTP.

## What is and isn't supported

Included: tenant-separated queue records, idempotent credit reservation, failed-job refund, explicit reviewer approval, invoice arithmetic validation, static AST scanning, defensive log analysis proposals, escaped HTML export, mock mode, an API client for OpenAI-compatible endpoints.

Not included: service-user login, SSO/MFA, distributed locking, web-facing authentication, payment processing, tax calculation, fully resilient job leasing, direct email sends, automatic firewall changes, remote tool execution, or verified GPU performance.

Use synthetic data for practice. On any production implementation, apply a security review, migrations, central secrets management, a retention schedule, tested restore procedures, monitoring, data protection analysis and change control.

## Troubleshooting

- `Run init first`: `python -m aiops init` and check `AIOPS_DB`.
- `Tenant unknown or insufficient credit`: create the tenant or increase credit using an authorized administrative workflow.
- `Model response too large`: inspect the model limits and reduce requested output.
- HTTP connection refused: verify the local server is bound to loopback and `curl http://127.0.0.1:8080/v1/models` works.
- Database locked: stop duplicate workers and investigate pending transactions; do not delete WAL files of a running database.
- HTML export empty: drafts must be manually approved before export.
