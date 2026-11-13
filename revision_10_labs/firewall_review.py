"""Defensive policy decision only; NEVER changes firewall rules.

The model's output is untrusted. Human approval and an independent executor
are required before applying a change. This module deliberately has no subprocess.
"""
from __future__ import annotations

import ipaddress


class PolicyReject(ValueError):
    pass


def review_proposal(ip_text: str, ttl_seconds: int, evidence_count: int,
                    protected_networks: tuple[str, ...] = ("1.1.1.0/24", "8.8.8.0/24")) -> dict:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        raise PolicyReject("Only a single literal IP address is permitted") from None
    if ip.version != 4 or not ip.is_global:
        raise PolicyReject("Reject non-public or non-IPv4 addresses")
    if not (60 <= ttl_seconds <= 900):
        raise PolicyReject("TTL must be 60..900 seconds")
    if evidence_count < 3:
        raise PolicyReject("Insufficient independent evidence")
    for item in protected_networks:
        if ip in ipaddress.ip_network(item, strict=True):
            raise PolicyReject("Protected network")
    return {"decision": "REVIEW_REQUIRED", "target": str(ip),
            "ttl_seconds": ttl_seconds, "evidence_count": evidence_count,
            "executed": False}
