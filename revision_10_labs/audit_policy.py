"""Allowlist-only audit events; rejects any attempt to store raw request content."""
from __future__ import annotations

import json
from datetime import datetime, timezone

ALLOWED_EVENTS = frozenset({"request_completed", "request_denied", "upstream_unavailable", "policy_rejected"})
ALLOWED_STATUS = frozenset({200, 400, 401, 403, 408, 409, 422, 429, 500, 502, 503, 504})


def make_event(event: str, status: int, duration_ms: int, request_id: str) -> dict:
    if event not in ALLOWED_EVENTS or status not in ALLOWED_STATUS:
        raise ValueError("Unknown event or status")
    if not 0 <= duration_ms <= 3_600_000:
        raise ValueError("Invalid duration")
    if not (1 <= len(request_id) <= 64 and request_id.isascii() and
            all(c.isalnum() or c in "-_" for c in request_id)):
        raise ValueError("Invalid request ID")
    return {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event, "status": status, "duration_ms": duration_ms,
            "request_id": request_id}


def encode_event(event: dict) -> str:
    if set(event) != {"timestamp", "event", "status", "duration_ms", "request_id"}:
        raise ValueError("Unexpected audit fields")
    return json.dumps(event, ensure_ascii=True, separators=(",", ":"))
