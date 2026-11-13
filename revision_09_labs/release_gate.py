"""Fail-closed release evidence evaluation with critical control handling."""
from dataclasses import dataclass
from collections.abc import Mapping, Iterable

ALLOWED = frozenset({"pass", "fail", "not_run", "waived"})


@dataclass(frozen=True)
class GateDecision:
    approved: bool
    blocked: tuple[str, ...]
    waived: tuple[str, ...]


def evaluate_gate(evidence: Mapping[str, str], required: Iterable[str],
                  critical: Iterable[str] = ()) -> GateDecision:
    required_set = set(required)
    critical_set = set(critical)
    if not required_set or not critical_set.issubset(required_set):
        raise ValueError("The required set must be nonempty and include critical checks")
    if not all(isinstance(x, str) and x for x in required_set | critical_set):
        raise ValueError("Evidence keys must be nonempty strings")
    if not all(value in ALLOWED for value in evidence.values()):
        raise ValueError("Unknown check result")
    blocked = tuple(sorted(key for key in required_set
                           if evidence.get(key, "not_run") != "pass"))
    waived = tuple(sorted(key for key in required_set if evidence.get(key) == "waived"))
    return GateDecision(approved=not blocked, blocked=blocked, waived=waived)
