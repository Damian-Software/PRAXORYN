"""Deterministic teaching model for an idempotent, auditable job state machine.

Production code must persist state and enforce transitions transactionally in SQL.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock

TRANSITIONS = {
    "queued": {"running", "canceled"},
    "running": {"succeeded", "failed", "canceled"},
    "failed": {"queued"},
    "succeeded": set(),
    "canceled": set(),
}

@dataclass
class Job:
    tenant_id: str
    job_id: str
    idempotency_key: str
    state: str = "queued"
    attempts: int = 0

class JobMachine:
    def __init__(self):
        self._jobs: dict[tuple[str, str], Job] = {}
        self._lock = RLock()

    def submit(self, tenant_id: str, job_id: str, idempotency_key: str) -> Job:
        if not all((tenant_id, job_id, idempotency_key)):
            raise ValueError("Missing identifiers")
        with self._lock:
            index = tenant_id, idempotency_key
            if index in self._jobs:
                return self._jobs[index]
            if any(x.tenant_id == tenant_id and x.job_id == job_id for x in self._jobs.values()):
                raise ValueError("Job ID already exists")
            job = Job(tenant_id, job_id, idempotency_key)
            self._jobs[index] = job
            return job

    def transition(self, job: Job, new_state: str) -> None:
        with self._lock:
            if new_state not in TRANSITIONS.get(job.state, set()):
                raise ValueError(f"Invalid transition: {job.state} -> {new_state}")
            if job.state == "failed" and new_state == "queued" and job.attempts >= 3:
                raise ValueError("Retry budget exceeded")
            if new_state == "running":
                job.attempts += 1
            job.state = new_state
