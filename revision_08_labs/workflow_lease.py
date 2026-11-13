"""Deterministic lease fencing demonstration, not transactional database storage."""
from __future__ import annotations
from dataclasses import dataclass
import secrets


@dataclass
class Job:
    state: str = 'queued'
    lease_token: str | None = None
    lease_until: int = 0
    result_ref: str | None = None

    def acquire(self, now: int, duration: int = 30) -> str:
        if duration <= 0 or duration > 3600:
            raise ValueError('Invalid lease duration')
        if self.state not in {'queued', 'leased'}:
            raise ValueError('Job is not leasable')
        if self.state == 'leased' and now < self.lease_until:
            raise ValueError('Lease is still active')
        self.lease_token = secrets.token_hex(16)
        self.lease_until = now + duration
        self.state = 'leased'
        return self.lease_token

    def complete(self, token: str, result_ref: str, now: int) -> bool:
        if (self.state != 'leased' or now >= self.lease_until
                or self.lease_token is None or token != self.lease_token):
            return False
        if not isinstance(result_ref, str) or not result_ref.startswith('artifact:'):
            return False
        self.state = 'completed'
        self.result_ref = result_ref
        return True
