# Before a production deployment

This is a lab, not a production certification.

1. Create a dedicated unprivileged account (`praxoryn`) with no interactive login.
2. Store work under `/var/lib/praxoryn-forge` owned by that user, mode 0700.
3. Install only reviewed code into `/opt/praxoryn-forge` and pin its release hash.
4. Check `python3 -m unittest discover -s tests -v` against that release.
5. Keep model API and ComfyUI on numeric loopback or a separately controlled private network.
6. Configure reverse proxy, authentication, TLS, and a centralized policy service before serving other users.
7. Do not place sensitive personal data in job inputs unless the data processing purpose, access, retention and deletion processes are approved.
8. The example queue lacks worker crash recovery and lease heartbeats; add those before multiple workers.
9. Use distinct accounts, databases and credential scopes for production tenants; tenant columns alone do not make a complete multitenant security boundary.
10. Rehearse restore from an encrypted backup. Monitor capacity, errors, queue age, ownership, and reviewer actions.

## Live inference

`FORGE_MODEL_URL=http://127.0.0.1:8080/v1 FORGE_MODEL_ID=<loaded-model-id> python3 -m forge --home /var/lib/praxoryn-forge run-once --backend local`

The URL must point to a separately managed existing chat completions server. **The lab does not fetch, train or host a model itself.**

## ComfyUI

- Start a local ComfyUI server separately and export an **API-format** workflow from its UI.
- Validate the workflow: `python3 tools/comfy_bridge.py --workflow my_api_workflow.json --dry-run`
- Inspect every custom node and its provenance before submitting the workflow. Never pass an unknown graph to a privileged service.
- Explicitly submit after approval: `python3 tools/comfy_bridge.py --workflow my_api_workflow.json --url http://127.0.0.1:8188 --poll`
- Do not use `workflows/example_api_shape.json` for live generation: it illustrates only the JSON shape and contains a deliberately nonexistent node type.
