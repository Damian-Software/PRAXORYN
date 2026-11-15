#!/usr/bin/env python3
"""Small deterministic sector exercises; no personal-data decisions by AI."""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from launchkit.security import Rejected
from launchkit.workflows import invoice_check, python_review


def require_object(value):
    if not isinstance(value, dict):
        raise Rejected("Expected a JSON object")
    return value


def require_list(value, field, max_count=200):
    if not isinstance(value, list) or len(value) > max_count:
        raise Rejected(f"{field} must be a list of up to {max_count} items")
    return value


def clean_ids(items, field="id"):
    identifiers = []
    for row in items:
        if not isinstance(row, dict) or not isinstance(row.get(field), str):
            raise Rejected(f"Each item needs string field {field}")
        identifiers.append(row[field])
    return identifiers


def evaluate(name: str, payload: dict) -> dict:
    require_object(payload)
    if name == "accounting":
        result = invoice_check(payload)
        return {"scenario": name, "result": result, "decision": "human_review"}
    if name == "software":
        result = python_review(payload)
        return {"scenario": name, "result": result, "decision": "developer_review"}
    if name == "education":
        rows = require_list(payload.get("resources"), "resources")
        role = payload.get("role", "guest")
        allowed = {"student": {"public", "course"}, "teacher": {"public", "course", "staff"},
                   "guest": {"public"}}
        if role not in allowed:
            raise Rejected("Unknown role")
        visible = [x["id"] for x in rows if isinstance(x, dict) and x.get("classification") in allowed[role]]
        return {"scenario": name, "visible_resources": visible, "note": "This is a teaching ACL, not a school SIS connector"}
    if name == "public_office":
        required = {"reference", "received_date", "document_type", "reply_channel"}
        missing = sorted(required - set(payload.keys()))
        return {"scenario": name, "missing_fields": missing, "routed": not missing,
                "decision": "human_officer_only"}
    if name == "insurance":
        present = set(clean_ids(require_list(payload.get("evidence"), "evidence")))
        expected = {"incident_form", "coverage_reference", "photo_evidence"}
        return {"scenario": name, "missing_evidence": sorted(expected - present),
                "decision": "human_claims_examiner_only"}
    if name == "retail":
        items = require_list(payload.get("products"), "products")
        ids = clean_ids(items, "sku")
        duplicates = sorted({x for x in ids if ids.count(x) > 1})
        return {"scenario": name, "duplicate_skus": duplicates,
                "missing_descriptions": [x["sku"] for x in items if not str(x.get("description", "")).strip()]}
    if name == "logistics":
        events = require_list(payload.get("deliveries"), "deliveries")
        late = []
        for item in events:
            due = datetime.fromisoformat(item["due_utc"].replace("Z", "+00:00"))
            actual = datetime.fromisoformat(item["received_utc"].replace("Z", "+00:00"))
            if due.tzinfo is None or actual.tzinfo is None:
                raise Rejected("Dates must include timezone")
            if actual > due:
                late.append({"id": item["id"], "seconds_late": int((actual - due).total_seconds())})
        return {"scenario": name, "late_deliveries": late, "decision": "operations_review"}
    if name == "manufacturing":
        machines = require_list(payload.get("machines"), "machines")
        warnings = [x["id"] for x in machines if x.get("status") in {"maintenance_due", "unknown"}]
        return {"scenario": name, "flagged_assets": warnings, "decision": "maintenance_technician_only"}
    if name == "health_admin":
        slots = require_list(payload.get("appointments"), "appointments")
        keys = [(x["room"], x["starts_at"]) for x in slots]
        duplicates = sorted({f"{a}|{b}" for a, b in keys if keys.count((a,b)) > 1})
        return {"scenario": name, "conflicting_slots": duplicates,
                "decision": "scheduler_review", "note": "No diagnosis, treatment or clinical inference"}
    if name == "hr_onboarding":
        tasks = require_list(payload.get("tasks"), "tasks")
        incomplete = [x["id"] for x in tasks if x.get("done") is not True]
        return {"scenario": name, "incomplete_tasks": incomplete,
                "decision": "hr_operator_only", "note": "No employment ranking or eligibility decision"}
    if name == "legal_admin":
        files = require_list(payload.get("documents"), "documents")
        allowed = {"contract", "evidence", "correspondence", "other"}
        invalid = [x["id"] for x in files if x.get("category") not in allowed]
        return {"scenario": name, "unclassified_documents": invalid,
                "decision": "qualified_person_review", "note": "Not legal analysis"}
    if name == "support":
        tickets = require_list(payload.get("tickets"), "tickets")
        allowed = {"new", "pending", "answered"}
        unknown = [x["id"] for x in tickets if x.get("state") not in allowed]
        return {"scenario": name, "invalid_state_tickets": unknown,
                "decision": "human_message_approval"}
    if name == "ai_provider":
        count, limit = payload.get("used_requests"), payload.get("monthly_request_limit")
        if not isinstance(count, int) or not isinstance(limit, int) or limit < 0 or count < 0:
            raise Rejected("Usage and limit must be nonnegative integers")
        return {"scenario": name, "limit_exceeded": count > limit,
                "remaining": max(0, limit - count), "note": "Not a payment or billing engine"}
    if name == "media_agency":
        files = require_list(payload.get("assets"), "assets")
        allowed = {"draft", "review", "approved", "rejected"}
        bad = [x["id"] for x in files if x.get("status") not in allowed]
        ready = [x["id"] for x in files if x.get("status") == "approved"]
        return {"scenario": name, "ready_to_package": ready, "invalid_status": bad,
                "decision": "publication_approval_required"}
    raise Rejected("Unsupported scenario")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario")
    parser.add_argument("input")
    parser.add_argument("--out")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(args.scenario, payload)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        target = Path(args.out)
        if target.exists():
            raise FileExistsError("Do not overwrite an existing report")
        target.write_text(output)
    print(output)

if __name__ == "__main__":
    main()
