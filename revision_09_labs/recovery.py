"""Deterministic RPO checks; not a backup or recovery engine."""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class RecoveryAssessment:
    acceptable: bool
    reason: str
    data_age_seconds: int | None


def assess_recovery_point(incident_at: datetime, snapshot_at: datetime,
                          rpo: timedelta, integrity_verified: bool) -> RecoveryAssessment:
    if incident_at.tzinfo is None or snapshot_at.tzinfo is None:
        raise ValueError("Both timestamps must contain an offset")
    if rpo <= timedelta(0):
        raise ValueError("RPO must be positive")
    age = incident_at - snapshot_at
    if age < timedelta(0):
        return RecoveryAssessment(False, "future_snapshot", None)
    seconds = int(age.total_seconds())
    if not integrity_verified:
        return RecoveryAssessment(False, "unverified_integrity", seconds)
    if age > rpo:
        return RecoveryAssessment(False, "rpo_exceeded", seconds)
    return RecoveryAssessment(True, "within_rpo", seconds)
