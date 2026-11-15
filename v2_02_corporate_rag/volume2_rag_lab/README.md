# Local AI RAG laboratory — volume II / stage 02

Purpose: implement a **single-tenant** document retrieval service with an existing `/v1/chat/completions` model endpoint. No container runtime, no autonomous shell access, no billing, and no open Internet binding.

## Files

- `app/rag_core.py` — ingestion, FTS5 index, retrieval, model adapter, citation gate.
- `app/rag_cli.py` — operator CLI (index, remove, search, ask, stats, check).
- `app/rag_api.py` — internal FastAPI endpoint `/v1/rag/answers`.
- `app/rag_backup.py` — SQLite online backup with integrity check.
- `ops/local-ai-rag.service` — service unit for Debian 13.
- `ops/rag.env.example` — environment **paths** only, no secret values.
- `ops/nginx-loopback.conf` — loopback proxy example, not public TLS.
- `ops/rag-smoke.sh` — authenticated request using loopback.
- `fixtures/docs` — entirely synthetic evidence data.
- `tests/test_rag.py` — offline unit tests and HTTP contract tests.

## Quick smoke test (no GPU needed)

```bash
cd volume2_rag_lab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m unittest discover -s tests -v
mkdir -p /tmp/vol2-rag-demo
python app/rag_cli.py --db /tmp/vol2-rag-demo/index.sqlite3 \
  --source-root fixtures/docs ingest incident.md
python app/rag_cli.py --db /tmp/vol2-rag-demo/index.sqlite3 \
  --source-root fixtures/docs search 'incident owner'
```

In this no-GPU smoke test, the `ask` subcommand cannot work until a compatible model is running on loopback and the operator has configured key files.

## Configuration for a local model

Use **two distinct secrets**: one for the public-facing internal RAG API and one for the upstream inference server (or existing local gateway). Keep their values out of shell history and documents. Create them with `openssl rand -hex 32 > /etc/local-ai/rag.token` under a restrictive umask, then apply reviewed ownership/mode. `RAG_APP_KEY_FILE` and `RAG_UPSTREAM_KEY_FILE` contain file paths, not the secret values.

Default `RAG_UPSTREAM_URL=http://127.0.0.1:8080`. Put the model ID from `GET /v1/models` into `RAG_MODEL`.

The RAG HTTP API uses its own `/v1/rag/answers` **application-specific** endpoint. The inference API remains the existing model backend: `POST /v1/chat/completions`.

## Security limitations

- FTS5 is **lexical** retrieval, not neural semantic search; synonyms and inflections may miss relevant text.
- The basic citation gate checks cited identifiers, **not factual entailment**. A plausible answer may still be wrong. Human review is required in high-stakes settings.
- SQLite stores raw document chunks. File-system permissions and disk encryption are required; no blanket claim of encrypted storage.
- The service supports one organization per instance. Do **not** build multi-tenant isolation solely from a caller-controlled request field; use isolated identities, databases, and explicit authorization.
- This is a tested offline laboratory, **not** an audited production deployment. Test concurrency, backup restore, TLS, load limits, retention and privacy controls before production.
- Never run the tests using production documents. Logs are designed to avoid prompts, but third-party reverse proxies or observability systems require independent configuration review.

## Systemd handoff

Install to `/opt/local-ai-rag/app`, create a virtual environment at `/opt/local-ai-rag/venv`, provision the dedicated service account `rag-reader`, a private state directory at `/var/lib/local-ai-rag`, approved source directory `/srv/local-ai-rag-docs`, secret files under `/etc/local-ai`, and a root-owned environment file at `/etc/local-ai/rag.env`. Run `sudo systemd-analyze verify /etc/systemd/system/local-ai-rag.service` before enabling it.

Run the first ingestion under the **same effective account** that will own the SQLite index. Do not create a root-owned `0600` database and expect an unprivileged web service to open it. Backups must be copied to a separate protected location and a restore must be tested.

## Evaluation fixture

`fixtures/eval.jsonl` contains four synthetic expected-source examples. After ingesting both fixtures:

```bash
python app/rag_eval.py --db /tmp/vol2-rag-demo/index.sqlite3 \
  --cases fixtures/eval.jsonl --k 4
```

The tool prints aggregate hit@k and negative rejection rate but **never the text of the evaluation questions**. The included tiny fixture is a smoke test, not a statistically meaningful accuracy result.
