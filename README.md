# PRAXORYN — Practical Local AI Engineering

**Author:** Damián Zelený  
**Book:** PRAXORYN — From model fundamentals to secure real-world deployment  
**Repository language:** English. The published book is available separately in Czech.

This is the book's companion-source repository. Its examples cover native Debian and WSL2 deployments, existing local-model APIs, Python and C++ code review, PHP/MariaDB integrations, RAG, controlled agents, documents and multimedia workflows.

> **Safety scope:** Reference projects are teaching laboratories. They are not automatically security-audited public services. Offline mock examples must not be mistaken for live AI inference or measured GPU performance. No Docker or Boost is required by these learning paths.

## Start with a practical project

| Project | Directory | Main purpose |
|---|---|---|
| AI Operations Field Kit | [aiops-fieldkit/](aiops-fieldkit/) | Tenant-scoped queue, approvals, invoices, code scanning and defensive proposals |
| Local API client labs | [api_labs/](api_labs/) | Calling existing local model APIs |
| Python/C++ CodeOps | [codeops/](codeops/) | AST scanning, optional Ruff/clang-tidy, JSON/HTML/SARIF |
| MediaOps | [praxoryn_mediaops/](praxoryn_mediaops/) | DOCX/PDF, synthetic previews and optional ComfyUI |
| Studio | [praxoryn_studio/](praxoryn_studio/) | Job workflow, approvals, media export |
| OpsBridge | [opsbridge/](opsbridge/) | Worker workflows and business tools |
| LaunchKit | [launchkit/](launchkit/) | Document generation, audit and tenant metadata |

## AI Operations Field Kit: quick start

```bash
git clone https://github.com/Damian-Software/PRAXORYN.git
cd PRAXORYN/aiops-fieldkit
python3 -m unittest discover -s tests -v
python3 -m aiops init
python3 -m aiops tenant org-alpha --credit 5
python3 -m aiops submit org-alpha summary case_487.txt --workspace ./examples --key request-000001
python3 -m aiops work --mock
python3 -m aiops job org-alpha 1
```

The 32 examples `case_487.txt` through `case_518.txt` are written in English.

## Additional companion laboratories

The printed book also references laboratory archives from Volume II and Volume III. A consolidated package named `PRAXORYN_COMPLETE_COMPANION_SOURCES_EN.zip` contains **13 separate laboratories**. Some older projects are **not yet browsable as individual source files in this GitHub repository**. See [the transparent coverage index](docs/COMPANION_SOURCE_COVERAGE.md).

To import a downloaded and verified copy of that package without overwriting repository files, use:

```bash
python3 tools/import_companion_bundle.py PRAXORYN_COMPLETE_COMPANION_SOURCES_EN.zip
python3 tools/import_companion_bundle.py PRAXORYN_COMPLETE_COMPANION_SOURCES_EN.zip --apply
```

The importer copies missing files into `companion-labs/` only after SHA-256 verification. It does not upload to GitHub automatically: review the changes before committing. The bundle is available from the book's author and must not be downloaded from untrusted mirrors.

## Security and support

- Keep model engines bound to loopback unless proper TLS, identity, quotas, auditing, and isolation are configured.
- Run untrusted code samples inside appropriate sandboxes; do not directly execute model-generated shell commands.
- Check model licenses and dependencies before commercial use.
- Use test data for labs; do not upload private prompts, keys or client records to public GitHub.
- Follow [the security notes](docs/SECURITY.md).
- See [the MediaOps-specific quick start](docs/MEDIAOPS_QUICKSTART.md).

**Maintainer:** Damián Zelený.
