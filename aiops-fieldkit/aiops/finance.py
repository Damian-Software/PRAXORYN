"""Deterministic invoice checks; not a tax-law engine."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import csv
from pathlib import Path

MONEY = Decimal("0.01")


def amount(value: str) -> Decimal:
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError("Invalid decimal value") from None
    if not number.is_finite() or abs(number) > Decimal("100000000000"):
        raise ValueError("Amount out of range")
    return number.quantize(MONEY, rounding=ROUND_HALF_UP)


def check_invoice_csv(path: str) -> dict:
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = set(reader.fieldnames or [])
        rows = list(reader)
    if len(rows) > 10000:
        raise ValueError("Too many rows")
    required = {"invoice_id", "quantity", "unit_price", "line_total"}
    if not required.issubset(fieldnames):
        raise ValueError("Missing CSV columns")
    issues, totals = [], {}
    for row_number, row in enumerate(rows, start=2):
        invoice_id = (row.get("invoice_id") or "").strip()
        if not invoice_id or len(invoice_id) > 80:
            issues.append({"row": row_number, "issue": "invalid_invoice_id"})
            continue
        try:
            quantity = Decimal(row["quantity"])
            if not quantity.is_finite() or quantity <= 0 or quantity > 100000:
                raise ValueError("invalid quantity")
            unit_price = amount(row["unit_price"])
            supplied = amount(row["line_total"])
            expected = (quantity * unit_price).quantize(MONEY, rounding=ROUND_HALF_UP)
            if expected != supplied:
                issues.append({"row": row_number, "issue": "line_mismatch", "expected": str(expected), "supplied": str(supplied)})
            totals[invoice_id] = totals.get(invoice_id, Decimal("0.00")) + expected
        except (ValueError, InvalidOperation, KeyError) as exc:
            issues.append({"row": row_number, "issue": "invalid_numeric_value"})
    return {"rows": len(rows), "issues": issues, "expected_totals": {k: str(v) for k, v in sorted(totals.items())}}
