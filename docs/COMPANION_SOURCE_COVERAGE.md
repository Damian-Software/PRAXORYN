# Companion-source coverage and recovery

This document audits the PRAXORYN book's supplied source archives against the public repository, as of 15 November 2026.

## Directly accessible on GitHub

- `aiops-fieldkit/` — now includes the original AI Operations Field Kit Python modules, CLI, 21 offline tests, operating-service examples and all 32 English case files.
- `api_labs/`, `revision_*_labs/`, `gateway/`, `codeops/`, `praxoryn_mediaops/`, `praxoryn_studio/`, `opsbridge/`, and `launchkit/` contain additional source files and examples.

## Supplied in the consolidated downloadable bundle, but not yet individually imported here

| Laboratory archive | Bundle directory | Primary content |
|---|---|---|
| `LOCAL_AI_SVAZEK_II_LAB_01.zip` | `labs/v2_01_provider_api/` | PHP provider API and tenant policies |
| `LOCAL_AI_SVAZEK_II_LAB_02.zip` | `labs/v2_02_corporate_rag/` | Local corporate RAG, retrieval and tests |
| `LOCAL_AI_SVAZEK_II_LAB_03.zip` | `labs/v2_03_email_crm_workflows/` | Email and CSV/CRM workflow |
| `LOCAL_AI_SVAZEK_II_LAB_04.zip` | `labs/v2_04_enterprise_workshops/` | Finance, security and developer workshops |
| `CASE_DESK_LAB_05.zip` | `labs/v2_05_casedesk/` | CaseDesk PHP/MariaDB app |
| `PRAXORYN_SVAZEK_II_LAB_07.zip` | `labs/v2_07_operations_handover/` | Service diagnostics and operations handover |
| `PRAXORYN_FORGE_LAB_05.zip` | `labs/v3_05_forge/` | Forge CLI and multimodal workflow tools |

The consolidated bundle also includes standalone snapshots of labs that are already represented by source modules in this repository: AIops, MediaOps, Studio, CodeOps, OpsBridge and LaunchKit. That is intentional: readers can extract and run each lab independently.

**Important:** The consolidated package is the current complete *delivery package*; until imported, GitHub's main branch must not be advertised as having every individual book lab file.

## English language policy

Code, documentation, prompts, and synthetic fixtures use English for reuse in different language editions. The author's name, Damián Zelený, is deliberately preserved with diacritics. The Czech-language book text is a separate localized product.

## Validation scope

The author-supplied lab archives were checked for file presence and Python parse errors. The Field Kit's 21 offline unit tests passed, as did the isolated tests for the missing laboratories where required tools were available. No real RTX 5080 benchmark or public production penetration test is implied.

## Import procedure

Use `tools/import_companion_bundle.py` with a trusted copy of `PRAXORYN_COMPLETE_COMPANION_SOURCES_EN.zip`. Start in dry-run mode. Review changes under `companion-labs/`, commit with Git and push using your own account permissions.

Avoid mixing unpublished projects into an existing application root. Each lab remains isolated in its named directory to prevent Python module, PHP route and configuration collisions.
