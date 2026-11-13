"""Safe draft packaging: no CRM mutation or direct send operation."""
from __future__ import annotations


def prepare_message(lead: dict, draft: str) -> dict:
    if not isinstance(lead, dict) or not isinstance(draft, str):
        raise ValueError('invalid input')
    if lead.get('opt_out') is not False or lead.get('approved_contact') is not True:
        return {'state': 'BLOCK', 'reason': 'no_contact_permission'}
    if len(draft) > 3000 or not draft.strip():
        return {'state': 'BLOCK', 'reason': 'invalid_draft'}
    return {'state': 'REVIEW_REQUIRED', 'lead_id': str(lead.get('id', '')),
            'message': draft.strip()}
