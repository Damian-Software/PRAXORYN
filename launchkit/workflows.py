"""Deterministic business rules; model outputs remain drafts awaiting review."""
from __future__ import annotations
import ast
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import StringIO
from pathlib import Path
from .security import Rejected
from .model import model_response

ALLOWED = {"memo", "invoice_check", "python_review", "media_plan"}


def run(kind: str, payload: dict, *, backend: str = "offline", config: dict | None = None) -> dict:
    if not isinstance(payload, dict) or kind not in ALLOWED:
        raise Rejected("Unknown workflow or invalid payload")
    if kind == "memo":
        note = payload.get("note", "")
        if not isinstance(note, str) or not (3 <= len(note) <= 5000):
            raise Rejected("note must be 3-5000 characters")
        if backend == "offline":
            return {"mode": "offline_fixture", "draft": "SYNTHETIC DEMO: " + note[:200], "requires_review": True}
        if backend != "local" or not config:
            raise Rejected("Backend must be offline or configured local")
        content = model_response(note, endpoint=config["endpoint"], model=config["model"],
                                 api_key=config.get("api_key", ""))
        return {"mode": "local_model", "draft": content, "requires_review": True}
    if kind == "invoice_check":
        return invoice_check(payload)
    if kind == "python_review":
        return python_review(payload)
    if kind == "media_plan":
        return media_plan(payload)
    raise AssertionError("Unreachable workflow")


def money(value: str) -> Decimal:
    if not isinstance(value, str):
        raise Rejected("Money must be supplied as a decimal string")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise Rejected("Invalid monetary value") from exc
    if not amount.is_finite() or abs(amount) > Decimal("1000000000"):
        raise Rejected("Monetary value outside laboratory range")
    if amount.as_tuple().exponent < -2:
        raise Rejected("More than two decimal places")
    return amount


def invoice_check(payload: dict) -> dict:
    rows = payload.get("rows")
    declared = payload.get("declared_total")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise Rejected("rows must contain 1-100 items")
    total = Decimal("0.00")
    detail = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or "quantity" not in row or "unit_price" not in row:
            raise Rejected("Each row requires quantity and unit_price")
        quantity = money(row["quantity"])
        price = money(row["unit_price"])
        if quantity < 0 or price < 0:
            raise Rejected("Negative quantities/prices require a separate credit note")
        subtotal = (quantity * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += subtotal
        detail.append({"line": idx, "subtotal": str(subtotal)})
    expected = money(declared)
    delta = total - expected
    return {"calculated_total": str(total), "declared_total": str(expected),
            "delta": str(delta), "matches": delta == 0, "lines": detail,
            "requires_review": True, "note": "Not tax, accounting or legal advice"}


def python_review(payload: dict) -> dict:
    code = payload.get("code", "")
    if not isinstance(code, str) or len(code.encode("utf-8")) > 32_000:
        raise Rejected("Python source must be <=32 KB")
    findings = []
    try:
        tree = ast.parse(code, filename="submitted.py")
    except SyntaxError as exc:
        return {"findings": [{"rule": "PY-SYNTAX", "line": exc.lineno,
                               "message": "Python syntax error"}], "requires_review": True}
    risky = {"eval": "PY-EVAL", "exec": "PY-EXEC", "compile": "PY-COMPILE"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in risky:
            findings.append({"rule": risky[node.func.id], "line": node.lineno,
                             "message": "Review dynamic code execution"})
    return {"findings": findings, "requires_review": True,
            "note": "Limited static triage; run Ruff and independent security review"}


def media_plan(payload: dict) -> dict:
    asset = payload.get("asset_type", "")
    if asset not in {"image", "video", "document"}:
        raise Rejected("asset_type must be image, video or document")
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str) or not (3 <= len(prompt) <= 3000):
        raise Rejected("prompt must be 3-3000 characters")
    return {"status": "plan_only", "asset_type": asset, "prompt_digest": __import__("hashlib").sha256(prompt.encode()).hexdigest(),
            "steps": ["approve_workflow", "queue_external_engine", "validate_artifacts", "human_review"],
            "requires_review": True,
            "note": "This does not execute ComfyUI or generate AI media"}
