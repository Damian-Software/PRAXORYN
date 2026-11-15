#!/usr/bin/env python3
"""Security event triage produces a proposed action, never changes the firewall."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import sys

MAX_BYTES = 2_000_000
VALID_EVENTS = {'auth_failed', 'rate_limited', 'request_allowed'}

class TriageError(Exception):
    pass


def scan(path: Path, threshold: int = 8) -> list[dict]:
    if threshold < 2 or threshold > 1000:
        raise TriageError('threshold must be 2..1000')
    if path.stat().st_size > MAX_BYTES:
        raise TriageError('log file too large for this laboratory')
    totals: dict[str, int] = defaultdict(int)
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            ip = ipaddress.ip_address(e['ip'])
        except (ValueError, KeyError, TypeError) as exc:
            raise TriageError(f'line {number}: invalid event') from exc
        if e.get('event') not in VALID_EVENTS or not isinstance(e.get('ts'), str):
            raise TriageError(f'line {number}: invalid event type/time')
        if not ip.is_global:
            continue  # Never propose blocking test, private, loopback or reserved IPs.
        if e['event'] in {'auth_failed', 'rate_limited'}:
            totals[str(ip)] += 1
    return [{'ip': addr, 'failures': count, 'proposal': 'REVIEW_NETWORK_RULE', 'executed': False}
            for addr, count in sorted(totals.items()) if count >= threshold]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('jsonl', type=Path)
    ap.add_argument('--threshold', type=int, default=8)
    ap.add_argument('--out', type=Path, default=Path('proposals.json'))
    args = ap.parse_args()
    try:
        actions = scan(args.jsonl, args.threshold)
        envelope = {'created_utc': datetime.now(timezone.utc).isoformat(), 'actions': actions,
                    'comment': 'No firewall change was executed; human approval required'}
        with args.out.open('x', encoding='utf-8') as fp:
            json.dump(envelope, fp, indent=2)
            fp.write('\n')
        print(json.dumps({'proposals': len(actions), 'executed': False}))
        return 0
    except (TriageError, FileNotFoundError, FileExistsError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
