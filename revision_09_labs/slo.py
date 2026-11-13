"""Offline service-level calculations for an explicitly defined request set."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR


@dataclass(frozen=True)
class SLOReport:
    eligible: int
    successful: int
    target: Decimal
    status: str
    availability: Decimal | None
    error_budget: int
    remaining_budget: int


def calculate_slo(eligible: int, successful: int, target: str = "0.999") -> SLOReport:
    if type(eligible) is not int or type(successful) is not int:
        raise TypeError("Counts must be integers")
    if eligible < 0 or successful < 0 or successful > eligible:
        raise ValueError("Counts must satisfy 0 <= successful <= eligible")
    try:
        target_value = Decimal(target)
    except Exception as exc:
        raise ValueError("Invalid SLO target") from exc
    if not target_value.is_finite() or not Decimal("0") < target_value <= Decimal("1"):
        raise ValueError("SLO target must be within (0, 1]")
    if eligible == 0:
        return SLOReport(eligible, successful, target_value, "no_data", None, 0, 0)
    allowed = int((Decimal(eligible) * (1 - target_value)).to_integral_value(rounding=ROUND_FLOOR))
    observed = eligible - successful
    availability = Decimal(successful) / Decimal(eligible)
    return SLOReport(eligible, successful, target_value,
                     "pass" if observed <= allowed else "fail",
                     availability, allowed, allowed - observed)
