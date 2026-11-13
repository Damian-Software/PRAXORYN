"""A simple read-only document access guard used by school and public-sector labs."""
from __future__ import annotations
from collections.abc import Mapping


def authorize_document(principal: Mapping, document: Mapping) -> bool:
    if principal.get('active') is not True:
        return False
    if not all(isinstance(principal.get(k), str) and principal.get(k) for k in ('tenant_id', 'subject_id')):
        return False
    if principal['tenant_id'] != document.get('tenant_id'):
        return False
    roles = principal.get('roles', [])
    audiences = document.get('allowed_roles', [])
    if not isinstance(roles, list) or not isinstance(audiences, list):
        return False
    if not any(role in audiences for role in roles if isinstance(role, str)):
        return False
    if document.get('sensitivity') not in {'public', 'internal', 'student_record', 'restricted_case'}:
        return False
    if document.get('sensitivity') == 'student_record':
        return bool(principal.get('educational_interest') is True)
    if document.get('sensitivity') == 'restricted_case':
        assignments = principal.get('assigned_case_ids', [])
        return isinstance(assignments, list) and isinstance(document.get('case_id'), str) and document['case_id'] in assignments
    return True


def filter_documents(principal: Mapping, docs: list[dict]) -> list[dict]:
    return [doc for doc in docs if authorize_document(principal, doc)]
