# LOCAL AI — revision 0.9 offline laboratories

This directory accompanies the reader-facing book *LOCAL AI* by Damián Zelený.

The examples exercise SLO calculations, admission control, backup-point assessment, release evidence, and manifest integrity. They use Python's standard library and synthetic data. They do not connect to inference APIs, install software, change firewall rules, read private information, run a database backup, or execute GPU benchmarks.

## Run

```bash
python3 -m unittest discover -s . -p 'test_revision_09.py' -v
python3 demo.py
```

## Limits

- Admission state is single-process and must not be substituted for distributed coordination.
- RPO assessment tests a declared point; it does not restore database content.
- Manifest hashing does not ensure an atomic snapshot of a directory changing concurrently.
- Release gate evidence is an illustration, not a signed CI/CD attestation.
- Explicitly validate all production integrations and permissions before deployment.
