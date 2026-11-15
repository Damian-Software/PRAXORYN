"""Minimal evidence completeness check. Does not decide insurance claims."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

REQUIRED={'property':['intake_form','damage_photos','policy_reference'],
          'travel':['intake_form','travel_confirmation','expense_receipts']}

def check_claim(record):
    if not isinstance(record,dict):raise ValueError('claim must be object')
    category=record.get('category')
    if category not in REQUIRED:raise ValueError('unknown claim category')
    supplied=record.get('document_types')
    if not isinstance(supplied,list) or not all(isinstance(x,str) for x in supplied):
        raise ValueError('invalid documents list')
    missing=sorted(set(REQUIRED[category])-set(supplied))
    return {'claim_id':str(record.get('claim_id',''))[:60],
            'missing_documents':missing,
            'state':'ready_for_human_review' if not missing else 'incomplete',
            'automated_decision':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('input');args=p.parse_args()
    print(json.dumps(check_claim(json.loads(Path(args.input).read_text())),indent=2))

if __name__=='__main__':main()
