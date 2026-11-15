"""A small, metadata-only SQLite audit journal."""
from __future__ import annotations
import sqlite3
import time
from contextlib import closing
from pathlib import Path

DDL = '''
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  ts INTEGER NOT NULL,
  operation TEXT NOT NULL,
  status TEXT NOT NULL,
  artifact_count INTEGER NOT NULL CHECK (artifact_count >= 0)
);
'''


def log_event(db: Path, operation: str, status: str, artifact_count: int = 0):
    if operation not in ('demo','live','health','export'):
        raise ValueError('unsupported operation')
    if status not in ('ok','error','skipped'):
        raise ValueError('unsupported status')
    db.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(db)) as con:
        con.execute(DDL)
        con.execute('INSERT INTO events(ts,operation,status,artifact_count) VALUES (?,?,?,?)',
                    (int(time.time()), operation, status, artifact_count))
        con.commit()


def show_events(db: Path) -> list[dict]:
    if not db.is_file():
        return []
    with closing(sqlite3.connect(db)) as con:
        con.row_factory=sqlite3.Row
        con.execute(DDL)
        return [dict(row) for row in con.execute('SELECT * FROM events ORDER BY id DESC LIMIT 30')]
