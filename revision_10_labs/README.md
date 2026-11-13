# Local AI: hands-on laboratories (revision 0.10)

All code, filenames, variables and output strings are English. 

## Workspace

- `scripts/00_preflight.sh`: read-only WSL/Debian/GPU preflight.
- `scripts/01_build_llama.sh`: source build of the existing llama.cpp server.
- `scripts/02_run_llama.sh`: loopback-only local server and API key file.
- `scripts/03_smoke.sh`: real chat completion call through existing API.
- `client.py`: stdlib-compatible API client with strict response checks.
- `bench.py`: warmup, sampling, median, p95 without fake performance claims.
- `audit_policy.py`: strict event allowlist; never persists payloads.
- `firewall_review.py`: policy-only defensive recommendation, no network modification.
- `config/`: native systemd, Nginx proxy, local PHP pilot, log rotation.
- `web/index.php`: CSRF-protected local pilot UI, trusts only authenticated reverse proxy.
- `sql/audit_metadata.sql`: minimal event-only metadata schema.
- `tests/test_revision_10.py`: offline tests with a mocked HTTP server.

## Quick run

```bash
bash scripts/00_preflight.sh
sudo apt update
sudo apt install -y git cmake ninja-build build-essential curl python3 nginx
# Install supported NVIDIA CUDA Toolkit for Debian 13 following NVIDIA docs.
# Do not install any Linux GPU driver inside WSL2.
LOCALAI_BACKEND=cuda bash scripts/01_build_llama.sh
export LOCALAI_MODEL="$HOME/models/your-licensed-model.gguf"
bash scripts/02_run_llama.sh
```

In another terminal:

```bash
bash scripts/03_smoke.sh
python3 bench.py --samples 10 --warmup 2 --output benchmark-first.json
python3 -m unittest discover -s tests -v
```

Use `LOCALAI_BACKEND=cpu` if CUDA is intentionally unavailable. `your-licensed-model.gguf` is a placeholder; acquisition and license review are the reader's explicit step. The server is loopback-only. For native production deployments, isolate service identities, terminate TLS and external identity at a trusted reverse proxy, back up data and prove restore, and audit the runtime permissions before exposure.

## Test scope

`python3 -m unittest discover -s tests -v` checks Python logic and mocked protocol handling. It does **not** prove WSL2/RTX 5080 performance, shell configuration on the target OS, GPU inference, production security or PHP-FPM isolation.
