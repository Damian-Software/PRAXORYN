"""Deliberately narrow input and output policy."""
from __future__ import annotations
from pathlib import Path
import re

KINDS = {"marketing", "education", "internal", "report"}
MAX_BRIEF_CHARS = 4_000
MAX_FILE_BYTES = 40 * 1024 * 1024


def safe_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("name must be a string")
    name = re.sub(r"[^a-zA-Z0-9_-]", "-", value.strip()).strip("-")
    if not name or len(name) > 64:
        raise ValueError("invalid name")
    return name


def validate_brief(brief: dict) -> dict:
    if not isinstance(brief, dict):
        raise ValueError("brief must be a JSON object")
    title = brief.get("title", "")
    prompt = brief.get("prompt", "")
    kind = brief.get("kind", "internal")
    if not isinstance(title, str) or not (1 <= len(title.strip()) <= 140):
        raise ValueError("title length invalid")
    if not isinstance(prompt, str) or not (1 <= len(prompt.strip()) <= MAX_BRIEF_CHARS):
        raise ValueError("prompt length invalid")
    if kind not in KINDS:
        raise ValueError("unsupported kind")
    return {"title": title.strip(), "prompt": prompt.strip(), "kind": kind}


def must_be_inside(root: Path, name: str) -> Path:
    root = root.resolve()
    target = (root / safe_name(name)).resolve()
    if target.parent != root:
        raise ValueError("invalid output path")
    return target
