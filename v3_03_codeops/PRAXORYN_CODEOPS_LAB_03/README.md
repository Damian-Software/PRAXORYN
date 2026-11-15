# PRAXORYN CodeOps — Python and C++ local code review

This independent educational project is designed for Debian 13, WSL2 Debian, and a native Linux server. No container runtime or Boost library required. It does not try to clone SonarQube's feature set. It combines explicit local checks, optional established CLI analyzers, a small declarative plugin system, optional local LLM explanation and exportable human-review reports.

## Quick start

```bash
cd PRAXORYN_CODEOPS_LAB_03
python3 -m unittest discover -s tests -v
python3 -m codeops.cli scan --project examples/demo_repo --output reports --plugin plugins/review_tokens.json
python3 -m codeops.cli scan --project examples/demo_repo --output reports-ci --ci
```

The demo intentionally contains unsafe Python patterns; `--ci` is expected to exit with status 1. Opening `reports/report.html` renders an escaped, local report.

## Optional established analyzers

```bash
sudo apt update
sudo apt install --no-install-recommends python3 python3-venv python3-pip pipx clang-tidy cmake ninja-build
pipx install ruff
# Optional, only from approved and pinned source: pipx install semgrep
cmake -S examples/demo_repo -B examples/demo_repo/build -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
python3 -m codeops.cli scan --project examples/demo_repo --output reports --require-tools ruff,clang-tidy
```

`clang-tidy` uses `examples/demo_repo/build/compile_commands.json`; a missing database produces `missing_compile_commands`, not a misleading clean bill of health. Ruff is optional for Python; the built-in Python AST rules remain available offline. `ruff` must be on `PATH` (under pipx, ensure `$HOME/.local/bin` is on PATH). Tool output is not an endorsement of the security of the scanned code.

## Optional local model review

Run an existing model server on the loopback interface exposing `POST /v1/chat/completions`; choose a model that your server actually lists. Do not use a public provider URL in this educational tool.

```bash
python3 -m codeops.cli scan --project examples/demo_repo --output reports-model \
  --model YOUR_LOCAL_MODEL_ID --base-url http://127.0.0.1:8080/v1
```

Set `LOCAL_AI_API_KEY` through your approved secret mechanism if the local server requires authentication. `model_review.md` is an explanation and never an automatic patch. The CodeOps client sends finding metadata only, not entire source files. The report contains tool coverage status; require analyzers explicitly in CI to prevent a missing program being silently treated as success.

## Plugins

This lab supports a **declarative plugin**: `plugins/review_tokens.json`. It contains simple opt-in string rules. To make a new plugin, copy that JSON, change `id` and `rules`, review its diff, then add the file path with `--plugin /absolute/path/rules.json`. The parser validates the schema and never imports executable Python from the plugin. For full-featured MCP tools, use the official Model Context Protocol SDK documentation. For editor extensions, use the respective marketplace, publisher information and extension signature/versions.

## Exit codes

`0`: scan completed; no high-severity findings, or quality gate was not enabled. `1`: `--ci` quality gate failed on at least one high or critical issue. `2`: configuration error or required analyzer is not `ok`. Reports must be reviewed regardless of exit status.

## Production checklist

Use a dedicated runner account, bounded filesystem view, protected source checkout, limits on file size and process execution time, approved tool versions, documented false-positive triage, manual patch review, and auditable CI gates. Review `docs/SECURITY.md` before feeding client code to any model.
