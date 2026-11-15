# Offline testing and verification

This repository contains educational reference applications. The commands below test software logic and configuration, not production security or GPU performance.

## AI Operations Field Kit

```bash
cd aiops-fieldkit
python3 -m unittest discover -s tests -v
python3 -m aiops init
python3 -m aiops tenant org-alpha --credit 5
python3 -m aiops submit org-alpha summary case_487.txt --workspace ./examples --key request-000001
python3 -m aiops work --mock
python3 -m aiops job org-alpha 1
```

Expected: the test suite passes and a queued case becomes `pending_review`. The `--mock` path does not call a real AI model.

## Other modules present in the repository

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests_studio -v
```

Run each command from the relevant laboratory root, with its documented dependencies. Some multimedia tests require FFmpeg and/or a document converter.

## Companion archive verification

```bash
python3 tools/import_companion_bundle.py PRAXORYN_COMPLETE_COMPANION_SOURCES_EN.zip
```

This command checks the SHA-256 manifest and reports which files would be imported. It does not write anything without `--apply`.

## Trust boundaries

- Unit tests do not prove public deployment readiness, GDPR compliance, or security audit completion.
- PHP, Nginx, and MariaDB examples require integration tests in the intended operating environment.
- Ruff, clang-tidy, CUDA, and ComfyUI require separate installations and versions.
- Never execute user-submitted code, model-generated shell commands, or firewall changes with unrestricted privileges.
- Live inference and RTX 5080 performance must be measured on the actual system.
