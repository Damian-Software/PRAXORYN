"""Measure end-to-end latency of a real local chat service; no invented tokens/s."""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path
from client import APIError, LocalChatClient, read_key


def percentile_nearest_rank(samples: list[float], p: float) -> float:
    if not samples or p <= 0 or p > 1:
        raise ValueError("Invalid samples/percentile")
    return sorted(samples)[max(0, __import__("math").ceil(p * len(samples)) - 1)]


def run(client: LocalChatClient, model: str, samples: int, warmup: int,
        prompt: str = "Reply with the word ready.") -> dict:
    if not 1 <= samples <= 100 or not 0 <= warmup <= 20:
        raise ValueError("Invalid run size")
    for _ in range(warmup):
        client.chat(prompt, model, 24)
    times = []
    for _ in range(samples):
        start = time.perf_counter()
        result = client.chat(prompt, model, 24)
        if not result:
            raise APIError("Empty model response")
        times.append((time.perf_counter() - start) * 1000)
    return {"samples": samples, "warmup": warmup,
            "median_ms": round(statistics.median(times), 2),
            "p95_ms": round(percentile_nearest_rank(times, .95), 2),
            "min_ms": round(min(times), 2), "max_ms": round(max(times), 2),
            "raw_ms": [round(t, 2) for t in times]}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8081")
    p.add_argument("--key-file", default=os.path.expanduser("~/.config/localai/api_keys.txt"))
    p.add_argument("--model", default="local-chat")
    p.add_argument("--samples", type=int, default=10)
    p.add_argument("--warmup", type=int, default=2)
    p.add_argument("--output", default="benchmark.json")
    a = p.parse_args()
    try:
        client = LocalChatClient(a.base_url, read_key(a.key_file), timeout=180)
        result = run(client, a.model, a.samples, a.warmup)
        out = Path(a.output)
        if out.exists():
            raise ValueError("Output exists; choose a new file to avoid overwriting evidence")
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "raw_ms"}, indent=2))
    except (APIError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
