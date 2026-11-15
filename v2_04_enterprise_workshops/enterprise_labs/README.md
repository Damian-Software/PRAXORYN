# Local AI — Volume II enterprise practical labs (Stage 04)

Author: Damián Zelený · Companion files to Chapters 326–391.

This package is intentionally container-free. It includes three standalone laboratories written primarily with Python's standard library, plus Bash/systemd examples. All code identifiers, comments and application-facing strings are in English for easier reuse across book translations.

## Prerequisites

- Debian 13 or Debian 13 running under WSL2 for the offline exercises
- Python 3, Git, Bash, curl; optional running local AI inference server exposing a compatible `/v1/chat/completions` endpoint
- A scratch directory and synthetic data only
- No real tenant secrets, company invoices, sensitive tickets, medical records or production repositories

The labs are examples, not a security certification or a turnkey public multi-tenant service.

## Start here

```bash
cd enterprise_labs
python3 -m unittest discover -s tests -v
bash ops/doctor.sh
bash ops/demo.sh
```

### Lab A — Developer review

```bash
bash samples/create_demo_repo.sh /tmp/localai-review-demo
python3 developer/review.py --repo /tmp/localai-review-demo --base main --preview
```

For a real local model call, set `LOCALAI_BASE_URL`, `LOCALAI_MODEL` and `LOCALAI_API_TOKEN` (do not commit the token), then omit `--preview`. This tool saves advisory text only. **It never executes or applies generated code.** It accepts a limited set of text file extensions, a bounded diff size and only strict HTTP loopback upstream URL forms in this educational release. The heuristic secret regex is not a DLP boundary.

### Lab B — Finance documents

```bash
python3 finance/invoices.py samples/invoice_items.csv --invoice-id DEMO001 --out /tmp/localai-finance-demo
python3 -m json.tool /tmp/localai-finance-demo/DEMO001.json
```

The example deliberately calculates using `Decimal` and creates only **DRAFT_REQUIRES_APPROVAL** artifacts. It is not a legally valid invoice system and does not calculate tax obligations for a specific jurisdiction. The two-file writer is not atomic. Add a transactional artifact lifecycle before production.

### Lab C — Security proposals

```bash
python3 security/triage.py samples/events.jsonl --threshold 4 --out /tmp/localai-triage-demo.json
python3 -m json.tool /tmp/localai-triage-demo.json
```

The program only writes **proposals** and marks all actions `executed=false`. It never calls nftables or changes firewall rules. This is a teaching example without production time-window correlation, tenant enrichment or incident approval infrastructure. The demonstration public IP address is only synthetic fixture data; never apply a real rule from it.

## Operational examples

`ops/localai-review.service.example` demonstrates systemd `Type=oneshot` and hardening. It assumes a real `/srv/review-repo` and appropriate privileges; copying the unit file alone does not create that repository. `ops/healthcheck.sh` verifies loopback `/v1/models`. `ops/backup_drafts.sh` creates a simple archive and checksum for file artifacts, not an atomic database snapshot. A production platform needs tested backup restore, access control, auditing, release pinning and authorization.

## Packaging and integrity

The parent release ZIP contains this lab package, the DOCX, PDF and Markdown manuscript, plus release manifest with SHA-256 checksums. Treat the manuscript as an editable technical publication and verify commands against the versions you have installed.
