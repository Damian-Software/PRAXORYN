"""Capacity and residency-aware selection over existing AI HTTP services."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    service_id: str
    capabilities: frozenset[str]
    local_only: bool
    context_limit: int
    ready: bool
    queue_depth: int


def choose_service(services: list[Service], capability: str,
                   context_tokens: int, require_local: bool = True) -> Service | None:
    if context_tokens < 0 or not capability:
        raise ValueError('Invalid request')
    eligible = [s for s in services if s.ready
                and capability in s.capabilities
                and context_tokens <= s.context_limit
                and (not require_local or s.local_only)
                and s.queue_depth >= 0]
    return min(eligible, key=lambda s: (s.queue_depth, s.service_id), default=None)
