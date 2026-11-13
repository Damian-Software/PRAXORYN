"""Claims workflow guard: AI output is advisory only and cannot change claim state."""
from __future__ import annotations

VALID_INPUT_STATES = {'received', 'review_in_progress'}


def prepare_review(claim: dict, ai_suggestion: dict) -> dict:
    if not isinstance(claim, dict) or claim.get('state') not in VALID_INPUT_STATES:
        return {'decision': 'REJECT', 'reasons': ['invalid_claim_state']}
    if not isinstance(ai_suggestion, dict):
        return {'decision': 'REJECT', 'reasons': ['invalid_suggestion']}
    evidence = ai_suggestion.get('evidence_ids')
    if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) and x for x in evidence):
        return {'decision': 'REVIEW', 'reasons': ['no_traceable_evidence']}
    allowed = set(claim.get('document_ids', []))
    if not all(item in allowed for item in evidence):
        return {'decision': 'REVIEW', 'reasons': ['evidence_outside_case']}
    # Only an authorized human reviewer or a formally approved deterministic
    # claims workflow may change any consequential business state.
    return {'decision': 'HUMAN_REVIEW', 'reasons': [], 'evidence_ids': evidence}
