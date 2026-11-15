"""Offline invoice arithmetic, not tax/legal/accounting advice."""
from __future__ import annotations
import argparse
import csv
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

MONEY = Decimal('0.01')

def check_invoice(csv_path, expected_total):
    issues = []
    amount = Decimal('0')
    with Path(csv_path).open(newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ['item_id','quantity','unit_price']:
            raise ValueError('expected item_id,quantity,unit_price columns')
        rows = list(reader)
    if len(rows) > 1000:
        raise ValueError('too many invoice lines')
    for index,row in enumerate(rows, start=2):
        try:
            qty=Decimal(row['quantity'])
            price=Decimal(row['unit_price'])
            if not (qty.is_finite() and price.is_finite()):
                raise InvalidOperation
            if qty<=0 or price<0 or qty>100000 or price>1000000:
                raise ValueError('out of permitted training range')
            line=(qty*price).quantize(MONEY, rounding=ROUND_HALF_UP)
            amount+=line
        except (InvalidOperation, ValueError, TypeError):
            issues.append({'line':index,'code':'invalid_amount'})
    total=amount.quantize(MONEY, rounding=ROUND_HALF_UP)
    reference=Decimal(str(expected_total))
    if total!=reference: issues.append({'code':'total_mismatch'})
    return {'calculated_total':str(total),'expected_total':str(reference),
            'status':'review' if issues else 'matched','issues':issues}


def main():
    p=argparse.ArgumentParser();p.add_argument('--csv',required=True)
    p.add_argument('--expected',required=True);p.add_argument('--output',default='invoice-report.json')
    args=p.parse_args()
    report=check_invoice(args.csv,args.expected)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(report['status']);raise SystemExit(0 if report['status']=='matched' else 2)

if __name__=='__main__':main()
