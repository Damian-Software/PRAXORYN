"""Read-only capability broker; no shell or network execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DeniedAction(PermissionError):
    """The proposed tool call was not authorized."""


@dataclass(frozen=True)
class Principal:
    principal_id: str
    capabilities: frozenset[str]


SERVICES = frozenset({"model", "worker", "gateway"})
ALIASES = ("assistant-default", "embedding-default")


def execute_proposal(principal: Principal, name: str, arguments: Any) -> dict:
    """Return a synthetic observation for an explicitly allowed read-only tool."""
    if not principal.principal_id:
        raise DeniedAction("Missing principal")
    if name not in {"get_service_status", "list_model_aliases"}:
        raise DeniedAction("Unknown tool")
    if name not in principal.capabilities:
        raise DeniedAction("Missing capability")
    if not isinstance(arguments, dict):
        raise DeniedAction("Invalid arguments")
    if name == "get_service_status":
        if set(arguments) != {"service"}:
            raise DeniedAction("Unexpected arguments")
        if not isinstance(arguments["service"], str):
            raise DeniedAction("Invalid service")
        if arguments["service"] not in SERVICES:
            raise DeniedAction("Unknown service")
        return {"service": arguments["service"], "status": "not_connected"}
    if arguments:
        raise DeniedAction("No arguments expected")
    return {"aliases": list(ALIASES)}
