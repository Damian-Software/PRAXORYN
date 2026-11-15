"""Administrative CLI; do not expose it to web users."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sqlite3
from rag_core import RagStore, RagConfig, answer, InputError, UpstreamError


def main() -> int:
    parser = argparse.ArgumentParser(description='Local document RAG administration')
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--source-root', required=True, type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('ingest', 'remove', 'search', 'ask'):
        a = sub.add_parser(action)
        a.add_argument('value')
    sub.add_parser('stats')
    sub.add_parser('check')
    args = parser.parse_args()
    os.umask(0o077)
    store = RagStore(args.db)
    try:
        if args.action == 'ingest':
            result = store.ingest(args.source_root, args.value)
        elif args.action == 'remove':
            result = {'removed': store.remove(args.value)}
        elif args.action == 'search':
            result = [{k:v for k,v in row.items() if k != 'text'}
                      for row in store.search(args.value)]
        elif args.action == 'ask':
            result = answer(store, args.value, RagConfig.from_env())
        elif args.action == 'stats':
            result = store.stats()
        else:
            result = {'integrity': store.conn.execute('PRAGMA integrity_check').fetchone()[0]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (InputError, UpstreamError, sqlite3.Error) as exc:
        print(json.dumps({'error': type(exc).__name__}, ensure_ascii=False))
        return 1
    finally:
        store.close()


if __name__ == '__main__':
    raise SystemExit(main())
