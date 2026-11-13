"""Allowlist-only structured audit event and keyed pseudonymous user identifier."""
from __future__ import annotations
import hashlib
import hmac
from datetime import datetime, timezone

EVENT_FIELDS = {"request_id", "tenant_id", "action", "outcome", "duration_ms", "engine_id"}
ACTIONS = {"chat", "embeddings", "image", "video", "document", "login", "job_cancel"}
OUTCOMES = {"accepted", "denied", "succeeded", "failed", "canceled"}


def pseudonymize(user_id: str, secret: bytes) -> str:
    if len(secret) < 32:
        raise ValueError("Audit HMAC key must be at least 32 bytes")
    if not user_id:
        raise ValueError("User ID required")
    return hmac.new(secret, user_id.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def audit_event(source: dict, user_id: str, secret: bytes) -> dict:
    required = {"request_id", "tenant_id", "action", "outcome"}
    if not required.issubset(source):
        raise ValueError("Required audit fields are missing")
    if source["action"] not in ACTIONS or source["outcome"] not in OUTCOMES:
        raise ValueError("Unknown audit action or outcome")
    clean = {key: source[key] for key in EVENT_FIELDS if key in source}
    if "duration_ms" in clean:
        value = clean["duration_ms"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 86400000:
            raise ValueError("Invalid duration")
    clean["user_tag"] = pseudonymize(user_id, secret)
    clean["timestamp"] = datetime.now(timezone.utc).isoformat()
    return clean
