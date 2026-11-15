# PRAXORYN LaunchKit - Debian 13 reference laboratory

A self-contained, **non-containerized educational project** demonstrating tenant isolation, scoped API keys, idempotency, a single SQLite worker, deterministic business checks, human approval, JSON artifacts and limited audit metadata. Python and code comments are in English. The accompanying book is in Czech. All samples contain synthetic data.

**Not a production security audit, payment engine, medical device or public internet service.** The HTTP process is intentionally restricted to `127.0.0.1`. The queue uses one worker; it has no distributed leases or automated crash recovery. The local audit hash chain requires external checkpointing for durable tamper evidence.

## Start on Debian 13

```bash
sudo apt update
sudo apt install --no-install-recommends python3 python3-venv python3-pip sqlite3 curl
python3 -m unittest discover -s tests -v
python3 -m launchkit --state ./private-state init
python3 -m launchkit --state ./private-state submit --tenant example --kind invoice_check --payload examples/invoice.json --key invoice0001
python3 -m launchkit --state ./private-state work-once --backend offline
python3 -m launchkit --state ./private-state audit-check
```

Find the new job ID in the JSON output. Inspect it and its artifact path:

```bash
python3 -m launchkit --state ./private-state show --tenant example --id <JOB_ID>
python3 -m launchkit --state ./private-state verify --tenant example --id <JOB_ID>
python3 -m launchkit --state ./private-state approve --tenant example --id <JOB_ID> --reviewer reviewer01
```

## HTTP demonstration

```bash
umask 077
python3 -m launchkit --state ./private-state issue-key --tenant example --scope read --label viewer01 > read.token
python3 -m launchkit --state ./private-state issue-key --tenant example --scope submit --label uploader01 > submit.token
python3 -m launchkit --state ./private-state serve --port 8787
# In a different terminal:
curl -H "Authorization: Bearer $(cat read.token)" http://127.0.0.1:8787/v1/jobs
```

Never store real secrets in a README, Git repository or public URL. In production the service identity, credential storage and key rotation need additional controls.

## Executable sector exercises

```bash
mkdir -p private-output
python3 -m tools.sector_ops accounting examples/scenarios/accounting.json --out private-output/accounting.json
python3 -m tools.sector_ops insurance examples/scenarios/insurance.json --out private-output/insurance.json
python3 -m tools.sector_ops software examples/scenarios/software.json --out private-output/software.json
```

All sector outputs are deterministic reference checks. They deliberately do not grant loans, decide insurance benefits, diagnose patients, grade pupils, rank job applicants or publish media automatically.

## Optional tools

- `tools/code_quality.py` wraps installed Ruff and clang-tidy with fixed executable arguments. It does not execute submitted source code.
- `tools/build_documents.py` uses python-docx (optional) and LibreOffice (optional) to produce DOCX and PDF from approved JSON.
- `tools/media_bridge.py` validates ComfyUI API JSON, sends a specifically approved graph, reads history and downloads a named output with a file signature check. `workflows/example_api_workflow.json` is **shape-only**: it cannot generate an image.
- `tools/backup_store.py` performs a SQLite Online Backup API copy and checks its integrity; it does not back up the separate artifacts directory.

## What must change before production

At minimum: independent TLS ingress, session/user identity, rate limits and quotas, key rotation/revocation UX, external audit checkpoints, encrypted off-host backups, worker leases/recovery, SIEM, schema migrations, request tracing without sensitive contents, role review, vulnerability assessment, source pinning, update/rollback and integration acceptance tests. School, public administration, insurance, health and employment deployments require sector-specific legal and human-governance review.
