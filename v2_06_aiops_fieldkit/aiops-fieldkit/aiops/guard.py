"""Generate defensive review candidates only; never modify firewall rules."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
from .core import is_public_address, json_record


def propose_from_jsonl(path: str, threshold: int = 6) -> list[dict]:
    if threshold < 2 or threshold > 100000:
        raise ValueError("threshold must be between 2 and 100000")
    counts = Counter()
    with Path(path).open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            if index >= 100000:
                raise ValueError("Too many log lines")
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ip = obj.get("remote_addr")
            status = obj.get("status")
            if not isinstance(ip, str) or not is_public_address(ip):
                continue
            try:
                code = int(status)
            except (ValueError, TypeError):
                continue
            if code in (401, 403, 429):
                counts[ip] += 1
    return [{"ip": ip, "events": count, "action": "review_only", "rule": "candidate_high_denial_rate"}
            for ip, count in sorted(counts.items()) if count >= threshold]
