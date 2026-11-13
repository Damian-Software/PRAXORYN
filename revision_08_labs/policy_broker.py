"""Offline policy broker lab: explicit capabilities, tenant boundaries, no shell."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
import json
import secrets
from typing import Any, Mapping


@dataclass(frozen=True)
class Principal:
    subject_id: str
    tenant_id: str
    roles: frozenset[str]
    groups: frozenset[str]


@dataclass(frozen=True)
class Resource:
    resource_id: str
    tenant_id: str
    classification: str
    allowed_groups: frozenset[str]


@dataclass(frozen=True)
class Approval:
    """A trusted-server-issued record, not something the model may create."""
    subject_id: str
    tenant_id: str
    action: str
    argument_digest: str
    expires_at: int


def argument_digest(arguments: Mapping[str, Any]) -> str:
    payload = json.dumps(arguments, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False)
    return sha256(payload.encode('utf-8')).hexdigest()


def approval_is_valid(approval: Approval | None, principal: Principal,
                      action: str, arguments: Mapping[str, Any], now: int) -> bool:
    return bool(approval is not None
                and approval.subject_id == principal.subject_id
                and approval.tenant_id == principal.tenant_id
                and approval.action == action
                and now < approval.expires_at
                and compare_digest(approval.argument_digest, argument_digest(arguments)))


CLASSIFICATIONS = {'public': 0, 'internal': 1, 'confidential': 2}


def can_read(principal: Principal, resource: Resource) -> bool:
    if principal.tenant_id != resource.tenant_id:
        return False
    if resource.classification not in CLASSIFICATIONS:
        return False
    if 'reader' not in principal.roles and 'admin' not in principal.roles:
        return False
    if resource.allowed_groups and not resource.allowed_groups.intersection(principal.groups):
        return False
    if resource.classification == 'confidential' and 'confidential-reader' not in principal.roles:
        return False
    return True


class DecisionLog:
    """Allowlisted event storage: no arguments, prompts, credentials or bodies."""
    def __init__(self) -> None:
        self.events: list[dict[str, str]] = []

    def record(self, action: str, outcome: str) -> str:
        if action not in {'knowledge.search', 'mail.draft', 'report.publish', 'unknown'}:
            action = 'unknown'
        if outcome not in {'allow', 'deny'}:
            raise ValueError('Unsupported outcome')
        decision_id = secrets.token_hex(8)
        self.events.append({'decision_id': decision_id, 'action': action,
                            'outcome': outcome})
        return decision_id


class Broker:
    """Reject unknown tools and fields before calling downstream components."""
    SCHEMAS = {
        'knowledge.search': {'query': str, 'collection_id': str, 'max_results': int},
        'mail.draft': {'recipient': str, 'subject': str, 'body': str},
        'report.publish': {'report_id': str, 'destination': str},
    }
    ROLE_PERMISSIONS = {
        'knowledge.search': {'reader', 'admin'},
        'mail.draft': {'mail-drafter', 'admin'},
        'report.publish': {'publisher'},
    }

    def __init__(self, logger: DecisionLog):
        self.logger = logger

    def authorize(self, principal: Principal, tool: str,
                  args: Mapping[str, Any], *, resource: Resource | None = None,
                  approval: Approval | None = None, now: int = 0) -> tuple[bool, str]:
        allowed = False
        schema = self.SCHEMAS.get(tool)
        if schema is not None and isinstance(args, dict) and set(args) == set(schema):
            valid_types = all(type(args[key]) is cls for key, cls in schema.items())
            valid_sizes = all(len(value) <= 4000 for value in args.values() if isinstance(value, str))
            valid_args = valid_types and valid_sizes
            if valid_args and self.ROLE_PERMISSIONS[tool].intersection(principal.roles):
                if tool == 'knowledge.search':
                    allowed = (resource is not None and can_read(principal, resource)
                               and args['collection_id'] == resource.resource_id
                               and 1 <= args['max_results'] <= 10
                               and 1 <= len(args['query'].strip()) <= 300)
                elif tool == 'mail.draft':
                    allowed = (len(args['subject']) <= 200 and len(args['body']) <= 4000
                               and args['recipient'].endswith('@example.test')
                               and '\n' not in args['recipient'] and '\r' not in args['recipient']
                               and 3 <= len(args['recipient']) <= 254)
                elif tool == 'report.publish':
                    allowed = approval_is_valid(approval, principal, tool, args, now)
        return allowed, self.logger.record(tool, 'allow' if allowed else 'deny')
