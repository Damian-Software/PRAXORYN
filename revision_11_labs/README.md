# Revision 0.11 — Practical Industry Integrations

Author: Damián Zelený.

## Offline prerequisite

Debian 13 or WSL2 Debian 13, Python 3.11+ (`python3 --version`). No third-party Python packages, containers, or Boost are required for the offline labs.

```bash
cd revision_11_labs
bash scripts/run_offline.sh
```

Every test uses synthetic data; none contacts a model, database server, payment provider, student system, or insurance ERP. The scripts may be executed without privileged permissions.

## Files and intended outcomes

- `invoice_check.py` and `fixtures/invoice_*.json`: validates arithmetic and formatting only. It must never approve tax treatment or post accounting entries.
- `review_gate.py` and `fixtures/code_checks_*.json`: prevents an AI review from bypassing deterministic unit, lint and security gates. It intentionally does not run untrusted code.
- `tenant_ledger.py`: atomic and idempotent local quota *reservations* with SQLite. Reservations are not final token usage, actual invoices or payment processing.
- `document_acl.py`: cross-tenant, role and case checks for retrieval. Use the same enforcement at every real document and embedding store query; this toy guard is not a complete identity service.
- `claim_triage.py`: restricts AI output to evidence-linked human review. Does not adjudicate, price or deny claims.
- `sales_draft.py`: produces an unsent draft, rejects opt-outs, and does not write to CRM.
- `sql/tenant_usage_mariadb.sql`: schema starting point for MariaDB/MySQL; migrate via approved DBA procedure after integration tests.
- `config/nginx_tenant_proxy.example.conf`: intentionally **returns 403**: safe by default, not an open internet gateway. Configure a vetted identity-bound reverse proxy and isolated upstream before releasing a paid service.

## Production acceptance checklist

Prove: tenant isolation, identity validation, authorization, schema validation, upstream API contract, provider terms and model licenses, traceable usage measurement, transaction safety, invoice reconciliation, refund handling, response content controls, abuse and fraud controls, TLS, customer contract and retention, secrets rotation, incident response, measured model concurrency, backups, and restore rehearsals. Do not mark any unexecuted check as passed.

Run `python3 school_demo.py` to show retrieval metadata filtering against the
four synthetic documents in `fixtures/school_documents.json`. This does not
implement a real RAG index or claim to anonymize actual school records.
