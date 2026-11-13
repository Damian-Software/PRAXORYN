"""Single-process illustrative admission control; not a distributed lock."""
from dataclasses import dataclass, field


@dataclass
class AdmissionController:
    capacity: int
    per_tenant_limit: int
    active: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if type(self.capacity) is not int or type(self.per_tenant_limit) is not int:
            raise TypeError("Limits must be integers")
        if self.capacity < 0 or self.per_tenant_limit < 0:
            raise ValueError("Limits must not be negative")

    def admit(self, job_id: str, tenant_id: str) -> bool:
        if not job_id or not tenant_id or not isinstance(job_id, str) or not isinstance(tenant_id, str):
            raise ValueError("Job and tenant identifiers are required")
        if job_id in self.active:
            return False
        if len(self.active) >= self.capacity:
            return False
        if sum(v == tenant_id for v in self.active.values()) >= self.per_tenant_limit:
            return False
        self.active[job_id] = tenant_id
        return True

    def release(self, job_id: str) -> None:
        if job_id not in self.active:
            raise KeyError("Unknown active job")
        del self.active[job_id]
