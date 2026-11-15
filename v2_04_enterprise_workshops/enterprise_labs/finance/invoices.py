#!/usr/bin/env python3
"""Deterministic invoice arithmetic and review-package creator; no AI amounts."""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import html
import json
import re
from pathlib import Path
import sys

CENT = Decimal('0.01')
MAX_LINES = 500

class InvoiceError(Exception):
    pass


def money(value: str) -> Decimal:
    if len(value) > 32:
        raise InvoiceError('numeric field too long')
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError):
        raise InvoiceError('invalid decimal amount')
    if not result.is_finite() or abs(result) > Decimal('1000000000'):
        raise InvoiceError('amount outside permitted range')
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate(rows: list[dict]) -> dict:
    if not rows or len(rows) > MAX_LINES:
        raise InvoiceError('invalid row count')
    net = Decimal('0.00'); tax = Decimal('0.00'); details = []
    for line_no, row in enumerate(rows, 1):
        name = str(row.get('description', '')).strip()
        if not name or len(name) > 120:
            raise InvoiceError(f'line {line_no}: description missing or too long')
        quantity = money(str(row.get('quantity', '')))
        unit_price = money(str(row.get('unit_price', '')))
        rate = money(str(row.get('tax_percent', '')))
        if quantity <= 0 or unit_price < 0 or rate < 0 or rate > Decimal('100'):
            raise InvoiceError(f'line {line_no}: invalid quantity, price or rate')
        line_net = (quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP)
        line_tax = (line_net * rate / Decimal('100')).quantize(CENT, rounding=ROUND_HALF_UP)
        net += line_net; tax += line_tax
        details.append({'description': name, 'net': str(line_net), 'tax': str(line_tax), 'rate': str(rate)})
    return {'lines': details, 'net': str(net), 'tax': str(tax), 'gross': str(net + tax), 'status': 'DRAFT_REQUIRES_APPROVAL'}


def load_csv(path: Path) -> list[dict]:
    if path.stat().st_size > 150000:
        raise InvoiceError('file too large')
    with path.open(newline='', encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        required = {'description', 'quantity', 'unit_price', 'tax_percent'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise InvoiceError('missing CSV columns')
        return list(reader)


def write_package(out_dir: Path, invoice_id: str, summary: dict) -> tuple[Path, Path]:
    if not re.fullmatch(r'[A-Za-z0-9]{1,30}', invoice_id):
        raise InvoiceError('invoice id must be 1..30 ASCII letters or numbers')
    out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = json.dumps({'invoice_id': invoice_id, **summary}, ensure_ascii=False, sort_keys=True, indent=2)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    data_path = out_dir / (invoice_id + '.json')
    html_path = out_dir / (invoice_id + '.html')
    # x mode avoids silent overwrite and provides a reviewable version record.
    with data_path.open('x', encoding='utf-8') as fp:
        fp.write(payload + '\n')
    rows_html = '\n'.join('<tr><td>' + html.escape(r['description']) + '</td><td>' + r['net'] + '</td><td>' + r['tax'] + '</td></tr>' for r in summary['lines'])
    document = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Invoice draft</title>'
                '<body><h1>Draft - approval required</h1><p>Reference: ' + html.escape(invoice_id) + '</p>'
                '<table><thead><tr><th>Item</th><th>Net</th><th>Tax</th></tr></thead><tbody>'
                + rows_html + '</tbody></table><p>Net: ' + summary['net'] + '</p><p>Tax: ' + summary['tax']
                + '</p><p>Total: ' + summary['gross'] + '</p><p>Source SHA-256: ' + digest
                + '</p></body></html>')
    with html_path.open('x', encoding='utf-8') as fp:
        fp.write(document)
    return data_path, html_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', type=Path)
    ap.add_argument('--invoice-id', required=True)
    ap.add_argument('--out', type=Path, default=Path('drafts'))
    args = ap.parse_args()
    try:
        summary = calculate(load_csv(args.csv))
        paths = write_package(args.out, args.invoice_id, summary)
        print(json.dumps({'status': 'draft_only', 'gross': summary['gross'], 'files': [str(x) for x in paths]}))
        return 0
    except (InvoiceError, FileNotFoundError, FileExistsError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
