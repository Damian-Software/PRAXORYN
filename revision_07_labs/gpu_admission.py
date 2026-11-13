"""Conservative VRAM admission estimator; not a hardware VRAM enforcement tool."""
from __future__ import annotations
from dataclasses import dataclass

GIB = 1024 ** 3

@dataclass(frozen=True)
class JobEstimate:
    job_id: str
    weights_gib: float
    kv_cache_gib: float
    scratch_gib: float
    other_gib: float = 0.0

    @property
    def estimated_gib(self) -> float:
        values = (self.weights_gib, self.kv_cache_gib, self.scratch_gib, self.other_gib)
        if not all(0 <= value < 1000 for value in values):
            raise ValueError("All memory estimates must be nonnegative and bounded")
        return sum(values)

class AdmissionPlanner:
    def __init__(self, physical_gib: float, reserve_gib: float):
        if not (0 < physical_gib < 1000 and 0 <= reserve_gib < physical_gib):
            raise ValueError("Invalid capacity or reserve")
        self.physical_gib = physical_gib
        self.reserve_gib = reserve_gib
        self.jobs: dict[str, JobEstimate] = {}

    @property
    def free_estimate_gib(self) -> float:
        return self.physical_gib - self.reserve_gib - sum(
            job.estimated_gib for job in self.jobs.values())

    def admit(self, job: JobEstimate) -> bool:
        if not job.job_id or job.job_id in self.jobs:
            raise ValueError("Job ID must be unique and nonempty")
        if job.estimated_gib > self.free_estimate_gib + 1e-9:
            return False
        self.jobs[job.job_id] = job
        return True

    def release(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)

if __name__ == "__main__":
    planner = AdmissionPlanner(physical_gib=16, reserve_gib=3)
    print("text:", planner.admit(JobEstimate("text", 6.5, 1.0, 1.0)))
    print("video:", planner.admit(JobEstimate("video", 7.0, 3.0, 2.0)))
    print("free_gib_estimate:", round(planner.free_estimate_gib, 2))
