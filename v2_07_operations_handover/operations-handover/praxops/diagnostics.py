"""Local-only summarization and release gates."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from statistics import median
from .metadata import read


def report(path: Path) -> dict:
    rows = read(path)
    samples = sorted(int(x["latency_ms"]) for x in rows if x["status"] == "ok")
    p95 = samples[min(len(samples) - 1, max(0, (95 * len(samples) + 99) // 100 - 1))] if samples else None
    return {"requests": len(rows), "statuses": dict(Counter(x["status"] for x in rows)), "median_ms": int(median(samples)) if samples else None, "p95_ms": p95}


def gate(path: Path, min_samples: int, max_error_rate: float, max_p95_ms: int) -> tuple[bool, list[str]]:
    data = report(path)
    reasons = []
    if data["requests"] < min_samples:
        reasons.append("insufficient_samples")
    errors = data["requests"] - data["statuses"].get("ok", 0)
    ratio = errors / data["requests"] if data["requests"] else 1.0
    if ratio > max_error_rate:
        reasons.append("error_rate_exceeded")
    if data["p95_ms"] is None or data["p95_ms"] > max_p95_ms:
        reasons.append("p95_exceeded")
    return len(reasons) == 0, reasons
