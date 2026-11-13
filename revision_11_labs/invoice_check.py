"""Example invoice verification. Deterministic checks; not a tax or accounting engine."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from dataclasses import dataclass
import json
from pathlib import Path

CENT = Decimal('0.01')


def money(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('amount must be a decimal string or integer')
    try:
        val = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid decimal amount') from exc
    if not val.is_finite() or val < 0 or val.as_tuple().exponent < -2:
        raise ValueError('amount must be non-negative with at most two decimal places')
    return val.quantize(CENT)


def inspect_invoice(doc: dict) -> dict:
    """No write-back and no tax-rate inference; monetary inputs are string amounts."""
    required = {'invoice_id', 'currency', 'lines', 'declared_total'}
    if not required <= doc.keys():
        return {'status': 'REVIEW', 'issues': ['missing_required_field']}
    if not isinstance(doc['invoice_id'], str) or not doc['invoice_id'].strip():
        return {'status': 'REVIEW', 'issues': ['invalid_invoice_id']}
    if not isinstance(doc['currency'], str) or len(doc['currency']) != 3 or not doc['currency'].isalpha():
        return {'status': 'REVIEW', 'issues': ['invalid_currency']}
    if not isinstance(doc['lines'], list) or not (1 <= len(doc['lines']) <= 1000):
        return {'status': 'REVIEW', 'issues': ['invalid_lines']}
    total = Decimal('0.00')
    try:
        for line in doc['lines']:
            if not isinstance(line, dict) or not {'quantity', 'unit_price'} <= line.keys():
                raise ValueError('invalid line')
            q = money(line['quantity'])
            price = money(line['unit_price'])
            total += (q * price).quantize(CENT, rounding=ROUND_HALF_EVEN)
        declared = money(doc['declared_total'])
    except (ValueError, TypeError, KeyError):
        return {'status': 'REVIEW', 'issues': ['invalid_amount']}
    return {'status': 'CHECKED' if total == declared else 'REVIEW',
            'issues': [] if total == declared else ['amount_mismatch'],
            'calculated_total': str(total), 'currency': doc['currency'].upper(),
            'invoice_id': doc['invoice_id']}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('invoice', type=Path)
    args = parser.parse_args()
    result = inspect_invoice(json.loads(args.invoice.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
