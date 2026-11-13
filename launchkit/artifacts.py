"""Per-tenant artifact paths and SHA-256 verification."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from .security import Rejected, slug, safe_json


def save_result(root: Path, tenant: str, identifier: str, result: dict) -> str:
    slug(tenant, "tenant")
    if len(identifier) != 32 or any(ch not in "0123456789abcdef" for ch in identifier):
        raise Rejected("Invalid job ID")
    target = root / "artifacts" / tenant / identifier
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    target.chmod(0o700)
    raw = (safe_json(result, limit=512_000) + "\n").encode()
    filepath = target / "result.json"
    with filepath.open("xb") as handle:
        handle.write(raw)
    filepath.chmod(0o600)
    digest = hashlib.sha256(raw).hexdigest()
    manifest = {"file": "result.json", "sha256": digest, "bytes": len(raw)}
    mf = target / "manifest.json"
    mf.write_text(safe_json(manifest) + "\n")
    mf.chmod(0o600)
    return f"{tenant}/{identifier}"


def verify_result(root: Path, tenant: str, identifier: str) -> bool:
    slug(tenant, "tenant")
    if len(identifier) != 32 or not all(c in "0123456789abcdef" for c in identifier):
        raise Rejected("Invalid job ID")
    target = root / "artifacts" / tenant / identifier
    mf = json.loads((target / "manifest.json").read_text())
    if mf.get("file") != "result.json":
        raise Rejected("Unexpected manifest filename")
    raw = (target / "result.json").read_bytes()
    return len(raw) == mf["bytes"] and hashlib.sha256(raw).hexdigest() == mf["sha256"]
