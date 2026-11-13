# LOCAL AI — Revision 0.7 companion laboratory

Standalone exercises for understanding capabilities, GPU memory admission, idempotent jobs, privacy-aware audit events, a MariaDB/MySQL schema and a restricted PHP status example.

* Python is intentionally standard-library-only; this is not an inference server.
* No package manager or network access is needed to run the unit tests.
* The provider catalog represents known endpoint conventions, **not** a guarantee for every deployed version.
* The VRAM planner is an estimator, not a driver limit or a true resource scheduler.
* The in-memory job machine is not transactional storage: use SQL transactions and unique constraints in production.
* PHP and systemd examples are illustrative and need authenticators, configuration and threat-model review before production.

## Tests

```bash
python3 -m unittest discover -s . -p 'test_revision_07.py' -v
python3 provider_registry.py
python3 gpu_admission.py
```

Examples and comments use English for translation portability. The accompanying book explains limitations, assumptions and practical evaluation.
