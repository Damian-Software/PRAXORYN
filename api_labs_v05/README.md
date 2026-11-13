# Local AI — Contract and authorization laboratory

This directory contains deliberately small, offline examples for teaching how to
validate model output and reject unauthorized tool proposals. It does not implement
an API server, an MCP server, a web application, or a production authentication system.

Requirements: Python 3.10+; standard library only.

Run the tests:

```bash
cd api_labs_v05
python3 -m unittest discover -v
```

Important limitations:
- `contracts.py` validates exactly one application-defined object, not the complete
  JSON Schema specification.
- `tool_broker.py` returns synthetic data and never launches a shell command.
- `audit.py` shows a minimal metadata-only event structure; do not interpret a
  pseudonymous principal reference as anonymous information.
- `../config/internal_proxy.nginx.example` listens only on loopback and provides
  NO authentication. Never expose it directly to an untrusted network.
- `../config/metadata_schema.sql` is a starter schema, not a complete enterprise
  authorization, retention, or migration design.

All comments, identifiers and error messages in code are written in English.
