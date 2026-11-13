# LOCAL AI — revision 0.8 security and RAG laboratory

This is a small, offline, standard-library-only teaching package accompanying *LOCAL AI* by Damián Zelený. It is **not** an inference service, a production authorization server, a real mail connector, or a secure sandbox for arbitrary commands. It does not run network requests, invoke a language model, manage a real database, or access your GPU.

## Run the exercises

```bash
python3 -m unittest discover -s . -p 'test_revision_08.py' -v
python3 demo.py
```

## Contents

- `policy_broker.py`: explicit tool registry, tenant/role/group checks, argument validation, fixed-shape decision log and approval binding demonstration.
- `rag_acl.py`: lexical search with ACL enforcement before scoring. It is intentionally *not* a vector database.
- `workflow_lease.py`: in-memory lease token fencing demonstration. The production equivalent requires durable transactions.
- `model_router.py`: local-only and capability-aware target selection; no remote fallback by default.
- `agent_jobs.sql`: reference schema for a transaction-backed queue and outbox; verify MariaDB/MySQL dialect and version.
- `localai-reader.service.example`: illustrative systemd restrictions; requires an actual worker and account.
- `test_revision_08.py`: negative security and state-transition regression tests.

The `Approval` object is trusted-server-issued in this test; it is **not a cryptographically signed delegation credential**. The broker is not connected to any real IdP. No real data or access tokens should be used with this lab. Before production use, add live identity validation, scoped service credentials, secured storage, transport security, monitoring, concurrency, audit policy, revocation, input/file isolation and a professional security review.
