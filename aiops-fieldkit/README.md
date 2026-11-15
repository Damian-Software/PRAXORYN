# AI Operations Field Kit — practical offline laboratory

This package accompanies Volume II of PRAXORYN. It is a reference implementation for learning and controlled internal experiments, not a certified public multi-tenant API service.

## Quick start on Debian 13

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip curl sqlite3
git clone https://github.com/Damian-Software/PRAXORYN.git
cd PRAXORYN/aiops-fieldkit
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

The `--mock` switch runs a deterministic simulation, not a model. For real inference use an existing locally hosted API:

```bash
export AI_BASE_URL=http://127.0.0.1:8080
export AI_MODEL=YOUR_MODEL_ID
# AI_API_KEY is optional if the local upstream requires authentication.
python -m aiops submit org-alpha reply support_request.txt --workspace ./examples --key request-000002
python -m aiops work
```

## Exercises

All 32 synthetic inputs referenced in the book are available at `examples/case_487.txt` through `examples/case_518.txt`. To submit one, replace `support_request.txt` in the submit example, and keep the `--workspace ./examples` boundary.

This CLI assumes a trusted local operator. It does not provide HTTP authentication, SSO, payments, distributed job leasing, or a security-audited public API. Do not expose it to untrusted customers or run it with real sensitive records without a formal review.

## Troubleshooting

- `Run init first`: run `python -m aiops init` and inspect `AIOPS_DB`.
- `Tenant unknown or insufficient credit`: verify that the tenant was created and quota is available.
- API connection refused: inspect `AI_BASE_URL`, `AI_MODEL`, and `curl http://127.0.0.1:8080/v1/models`.
- Database locked: identify competing workers; do not remove live WAL files.
- Empty HTML export: review and approve a draft first.
