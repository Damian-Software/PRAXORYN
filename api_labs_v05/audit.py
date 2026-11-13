"""Minimal metadata-only audit-event shape."""
from __future__ import annotations

import uuid

EVENT_FIELDS = frozenset({
    "event", "request_id", "principal_ref", "decision", "reason_code"
})
REASON_CODES = frozenset({"allowed", "not_authorized", "invalid_contract"})


def make_event(request_id: str, principal_ref: str,
               decision: str, reason_code: str) -> dict[str, str]:
    uuid.UUID(request_id)
    if decision not in {"allow", "deny"}:
        raise ValueError("Invalid decision")
    if reason_code not in REASON_CODES:
        raise ValueError("Invalid reason code")
    if not principal_ref or len(principal_ref) > 100:
        raise ValueError("Invalid principal reference")
    return {
        "event": "tool_decision",
        "request_id": request_id,
        "principal_ref": principal_ref,
        "decision": decision,
        "reason_code": reason_code,
    }
