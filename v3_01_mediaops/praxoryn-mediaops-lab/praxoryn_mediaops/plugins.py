"""Allowlisted read-only tools; never execute arbitrary model-proposed shell commands."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from pathlib import Path
import csv


def invoice_sum(values: list[str]) -> str:
    if len(values) > 1000:
        raise ValueError('too many items')
    try:
        numbers = [Decimal(x) for x in values]
    except (InvalidOperation,TypeError):
        raise ValueError('invalid decimal') from None
    if any(not x.is_finite() for x in numbers):
        raise ValueError('non-finite amount')
    return str(sum(numbers, Decimal('0.00')).quantize(Decimal('0.01')))


def catalog_lookup(path: Path, sku: str) -> dict | None:
    if not sku.isascii() or len(sku) > 64:
        raise ValueError('invalid SKU')
    with path.open(newline='', encoding='utf-8') as f:
        for record in csv.DictReader(f):
            if record.get('sku') == sku:
                return {key: record.get(key,'') for key in ('sku','name','price')}
    return None

TOOLS = {'invoice_sum': invoice_sum, 'catalog_lookup': catalog_lookup}


def run_tool(name: str, **kwargs):
    if name not in TOOLS:
        raise PermissionError('tool not on approved list')
    return TOOLS[name](**kwargs)
