#!/usr/bin/env python3
"""Summarize metadata-only JSONL benchmark records."""
import argparse
import json
import math
import statistics
from pathlib import Path


def nearest_rank(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    if not 0 < percentage <= 100:
        raise ValueError('Percentage must be within (0, 100]')
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentage / 100) - 1)]


def summarize(rows: list[dict]) -> dict:
    successes = [r for r in rows if r.get('ok') is True]
    times = [float(r['latency_ms']) for r in successes
             if type(r.get('latency_ms')) in (int, float) and r['latency_ms'] >= 0]
    tps = [float(r['tokens_per_second_e2e']) for r in successes
           if type(r.get('tokens_per_second_e2e')) in (int, float)
           and r['tokens_per_second_e2e'] >= 0]
    return {
        'requests': len(rows), 'successes': len(successes),
        'success_rate': len(successes) / len(rows) if rows else None,
        'p50_latency_ms': statistics.median(times) if times else None,
        'p95_latency_ms': nearest_rank(times, 95),
        'mean_latency_ms': statistics.mean(times) if times else None,
        'mean_e2e_tokens_per_second': statistics.mean(tps) if tps else None,
        'latency_samples': len(times), 'token_samples': len(tps),
        'warning': 'p95 is unstable for small samples' if len(times) < 20 else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.file.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        parser.error('Expected JSON objects')
    print(json.dumps(summarize(rows), indent=2))


if __name__ == '__main__':
    main()
