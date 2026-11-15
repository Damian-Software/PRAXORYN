"""Metadata-only local probe log: no prompts, responses, keys or emails."""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALLOWED = {"timestamp", "operation", "status", "latency_ms", "model_tag"}


def append(path: Path, event: dict) -> None:
    if set(event) != ALLOWED:
        raise ValueError("Only explicitly approved operational fields may be logged")
    if event["status"] not in ("ok", "unavailable", "invalid", "transport"):
        raise ValueError("Unsupported status")
    if not isinstance(event["latency_ms"], int) or not 0 <= event["latency_ms"] < 2_000_000:
        raise ValueError("Invalid latency")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, (json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
    finally:
        os.close(fd)


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            item = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"Invalid metadata line {i}") from exc
        if not isinstance(item, dict) or set(item) != ALLOWED:
            raise ValueError(f"Unexpected metadata fields on line {i}")
        events.append(item)
    return events


def retain(path: Path, days: int, now: datetime | None = None) -> tuple[int, int]:
    if not 1 <= days <= 365:
        raise ValueError("Retention must be between 1 and 365 days")
    now = now or datetime.now(timezone.utc)
    threshold = now - timedelta(days=days)
    all_events = read(path)
    keep = []
    for item in all_events:
        moment = datetime.fromisoformat(str(item["timestamp"]).replace("Z", "+00:00"))
        if moment.tzinfo is None:
            raise ValueError("Timestamp is missing a time zone")
        if moment >= threshold:
            keep.append(item)
    if path.exists():
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as f:
            for event in keep:
                f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    return len(all_events), len(keep)
