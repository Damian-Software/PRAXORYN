"""Offline lexical retrieval evaluation; never prints private questions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from rag_core import RagStore, InputError


def evaluate(store: RagStore, cases: list[dict], k: int = 4) -> dict:
    if not 1 <= k <= 8:
        raise InputError('Invalid evaluation k')
    if not cases:
        raise InputError('Evaluation set must not be empty')
    count = 0
    hits = 0
    negatives = 0
    negative_passes = 0
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'question','expected_source'}:
            raise InputError('Invalid case schema')
        question, expected = case['question'], case['expected_source']
        if not isinstance(question, str) or not (2 <= len(question) <= 1000):
            raise InputError('Invalid question')
        if expected is not None and not isinstance(expected, str):
            raise InputError('Invalid expected source')
        found = store.search(question, k)
        count += 1
        if expected is None:
            negatives += 1
            negative_passes += int(not found)
        else:
            hits += int(expected in [f['source'] for f in found])
    positive = count - negatives
    return {
        'cases': count,
        'positive_cases': positive,
        'negative_cases': negatives,
        'hit_at_k': round(hits / positive, 3) if positive else None,
        'negative_rejection_rate': round(negative_passes / negatives, 3) if negatives else None
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--k', type=int, default=4)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding='utf-8').splitlines()
             if line.strip()]
    store = RagStore(args.db)
    try:
        print(json.dumps(evaluate(store, cases, args.k), indent=2))
    finally:
        store.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
