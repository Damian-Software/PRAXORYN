# Release-readiness checklist (local training)

## Baseline
- [ ] Debian release, Python version and package provenance recorded
- [ ] No containers; application uses a non-privileged service account
- [ ] WSL2 vs bare-metal distinctions documented
- [ ] Local HTTP and model endpoint remain restricted to loopback
- [ ] Offline operation succeeds and is distinguishable from live inference

## Data and access
- [ ] Per-tenant API keys issued with smallest possible scope
- [ ] Cross-tenant negative requests tested
- [ ] Key rotation and revocation procedure reviewed
- [ ] Only approved metadata in audit; no credentials in logs
- [ ] Data inventory, purposes, lawful basis and retention approved

## Operations
- [ ] Service and timer paths reviewed using systemd-analyze verify
- [ ] Backups stored off-host and encrypted; restore drill completed
- [ ] SQLite and artifacts restored as a coherent set
- [ ] Failure response recorded for model outage and lost worker
- [ ] Human approval before release is independently auditable

## Optional adapters
- [ ] Ruff/clang-tidy outputs reviewed by a developer
- [ ] ComfyUI graph exported in API format and validated on actual version
- [ ] Media output verified with ffprobe and SHA-256
- [ ] DOCX/PDF visually inspected in each language edition
- [ ] MCP/plugin dependencies and their privileges reviewed and pinned

A passed checklist in a lab does not imply certification for public production.
