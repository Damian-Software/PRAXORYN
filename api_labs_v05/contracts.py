"""Small, auditable contract checks for a local AI demonstration.

This is not a general-purpose JSON Schema implementation.
"""
from __future__ import annotations

import json
from typing import Any

CATEGORIES = frozenset({"hardware", "software", "access", "other"})
PRIORITIES = frozenset({"low", "normal", "high"})
FIELD_NAMES = frozenset({"category", "priority", "reason"})
MAX_RESPONSE_BYTES = 4096


class ContractError(ValueError):
    """Raised when a model output violates the application contract."""


def validate_ticket(raw: str) -> dict[str, str]:
    if not isinstance(raw, str):
        raise ContractError("Response must be a string")
    if len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ContractError("Response exceeds the byte limit")
    try:
        value: Any = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ContractError("Invalid JSON") from exc
    if not isinstance(value, dict):
        raise ContractError("Expected a JSON object")
    if frozenset(value) != FIELD_NAMES:
        raise ContractError("Unexpected or missing fields")
    if not isinstance(value["category"], str) or value["category"] not in CATEGORIES:
        raise ContractError("Invalid category")
    if not isinstance(value["priority"], str) or value["priority"] not in PRIORITIES:
        raise ContractError("Invalid priority")
    if not isinstance(value["reason"], str):
        raise ContractError("Invalid reason type")
    if not (1 <= len(value["reason"]) <= 240):
        raise ContractError("Invalid reason length")
    return value
