"""Explicit input validation and scoped, non-reversible API-key storage."""
from __future__ import annotations
import hashlib
import hmac
import json
import re
import secrets
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9_-]{1,47}$")
SCOPES = frozenset({"read", "submit", "approve", "admin"})

class Rejected(ValueError):
    pass


def slug(text: str, kind: str = "identifier") -> str:
    if not isinstance(text, str) or not NAME.fullmatch(text):
        raise Rejected(f"Invalid {kind}: expected 2-48 ASCII characters")
    return text


def safe_json(value, *, limit: int = 65536) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > limit:
        raise Rejected("JSON payload is too large")
    return encoded


def make_key() -> str:
    return "pxr_" + secrets.token_urlsafe(36)


def key_digest(key: str) -> str:
    if not isinstance(key, str) or not key.startswith("pxr_"):
        raise Rejected("Invalid key format")
    return hashlib.sha256(key.encode("ascii")).hexdigest()


def validate_key(candidate: str, digest: str) -> bool:
    try:
        return hmac.compare_digest(key_digest(candidate), digest)
    except (Rejected, UnicodeEncodeError):
        return False


def prepare_private_dir(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_symlink():
        raise Rejected("State root must not be a symbolic link")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def restrict_path(base: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or len(rel) > 128:
        raise Rejected("Invalid relative path")
    if rel.startswith(("/", ".")) or "\\" in rel or ".." in Path(rel).parts:
        raise Rejected("Paths must be flat, relative names")
    if len(Path(rel).parts) != 1:
        raise Rejected("Subdirectories are not permitted")
    return base.resolve() / rel
