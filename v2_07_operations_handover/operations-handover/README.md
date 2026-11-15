# PRAXORYN — Operations Handover Lab

A practical, local-only companion to chapters 537 onward in **Volume II**.
All application code, comments, identifiers and sample input are in English.
This is an instructional operator toolkit, **not** an internet-facing multi-tenant API gateway or a security certificate.
It uses Python 3 standard library and an existing chat-completions-compatible local inference API. No container runtime is needed.

## 1. Offline exercise (two terminals)

```bash
cd operations-handover
python3 -m unittest discover -s tests -v
python3 -m praxops.mock_server
```

In a second terminal:

```bash
cd operations-handover
python3 -m praxops --url http://127.0.0.1:8765 health
python3 -m praxops --url http://127.0.0.1:8765 models
python3 -m praxops --url http://127.0.0.1:8765 probe --count 8
python3 -m praxops report
python3 -m praxops gate --min-samples 5 --max-error-rate 0.1 --max-p95-ms 5000
python3 -m praxops retain --days 14
```

The mock returns the fixed token `READY` and runs only on `127.0.0.1`. Its output is not a model benchmark.

## 2. Local existing model server

Start your own llama.cpp server separately and check its actual advertised model ID first:

```bash
python3 -m praxops --url http://127.0.0.1:8080 health
python3 -m praxops --url http://127.0.0.1:8080 models
PRAXOPS_MODEL='REPLACE_MODEL_ID' python3 -m praxops --url http://127.0.0.1:8080 probe --count 3
```

Never expose the demo endpoint publicly; the client deliberately rejects non-loopback origins. Use an authenticated gateway and TLS for real customers.

## 3. Logs, data and safety

Probe log: `./private/probes.jsonl` with filesystem mode `0600` where created by the tool. It contains only timestamp, operation, status, latency and a model label. Avoid identifiable model labels. The probe prompt is synthetic. **Do not send real customer data.**
Retention is a local file operation and may need to be extended to backups and archives.
Tests are offline; production security, uptime and GPU performance are unverified until measured in the target environment.

## 4. Notes on service installation

`ops/` contains examples only. Adjust paths, effective users, secrets and `ReadWritePaths`/`StateDirectory` to your real host. Run `systemd-analyze verify` and inspect `systemd-analyze security` before enabling. WSL2 is useful for exercises, but is not an SLA-equivalent replacement for a dedicated server.
