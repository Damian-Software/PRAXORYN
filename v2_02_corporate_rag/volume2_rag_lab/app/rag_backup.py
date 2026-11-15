"""Consistent snapshot using SQLite online backup API; offline integrity check required."""
import argparse
import os
from pathlib import Path
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('database', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if not args.database.is_file() or args.destination.exists():
        parser.error('Database must exist; destination must be new')
    os.umask(0o077)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(args.database)) as src:
        with sqlite3.connect(str(args.destination)) as dst:
            src.backup(dst)
            assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    os.chmod(args.destination, 0o600)
    print('Backup completed and integrity-checked')


if __name__ == '__main__':
    main()
