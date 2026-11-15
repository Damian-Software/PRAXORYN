# Praxoryn Forge — educational reference

A no-container, Python standard-library-first integration lab. Not a publicly audited production service. English code and comments.

## Quick start (Debian 13)

```bash
cd PRAXORYN_FORGE_LAB_05
python3 -m unittest discover -s tests -v
python3 -m forge --home ./private-state demo
python3 -m forge --home ./private-state audit --tenant example
```

To run separate operations, copy `examples/*.csv`, `.py`, `.cpp`, `.txt` into `private-state/inputs/` and then:

```bash
python3 -m forge --home ./private-state submit --tenant example --plugin code --payload examples/code.json --key code-check-0001
python3 -m forge --home ./private-state run-once --backend offline
```

Use `show` with the returned job ID. Human approval is mandatory; `review` requires a reviewer label. No operation sends emails, executes submitted source code, edits firewall rules or pays invoices.

### Safety limitations

- The SQLite queue is intended for **one local worker** in this teaching package. Deploying multiple workers requires crash leases and a recovery process.
- Work payloads are stored in SQLite; audit entries store only selected metadata. Treat the database and output directory as confidential.
- `--backend local` calls an **existing** HTTP chat completions API on numeric loopback only. It does not install or start a model.
- Output is a draft for explicit human review. A passed test suite is not a security certification.
- ComfyUI video/image generation is covered in the book as a separate adapter and requires a validated workflow; no fake model media files are produced by this lab.
