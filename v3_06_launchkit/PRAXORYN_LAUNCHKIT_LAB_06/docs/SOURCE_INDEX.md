# Source index

- `launchkit/security.py`: validation and key derivation
- `launchkit/db.py`: SQLite schema, audit, jobs and scoped access
- `launchkit/worker.py`: one-job state transition and result storage
- `launchkit/workflows.py`: deterministic accounting, Python AST, media planning and model draft
- `launchkit/model.py`: connector for existing local chat completion API
- `launchkit/api.py`: loopback HTTP endpoints and role checks
- `launchkit/__main__.py`: CLI used in the book
- `launchkit/artifacts.py`: manifest and SHA-256 validation
- `tools/sector_ops.py`: 14 runnable sector exercises with synthetic data
- `tools/media_bridge.py`: ComfyUI API-format validation and transfer
- `tools/code_quality.py`: Ruff and clang-tidy wrappers
- `tools/build_documents.py`: DOCX/PDF export from approved JSON
- `tools/backup_store.py`: SQLite backup and integrity verification
- `ui/index.php`: read-only, non-public PHP demonstration
- `ops/`: systemd, timer, local Nginx and quickstart
- `tests/`: offline regression suite
