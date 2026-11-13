"""Offline tenant quota and idempotent charge reservation example using SQLite.

For teaching only. Reserve semantics are local; a charge still needs upstream success
reconciliation, a durable event queue, actual measured token usage, and external billing.
"""
from __future__ import annotations
import hashlib
import hmac
import sqlite3
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY, monthly_token_limit INTEGER NOT NULL CHECK (monthly_token_limit >= 0),
    used_tokens INTEGER NOT NULL DEFAULT 0 CHECK (used_tokens >= 0)
);
CREATE TABLE IF NOT EXISTS reservations (
    tenant_id TEXT NOT NULL, request_id TEXT NOT NULL, reserved_tokens INTEGER NOT NULL CHECK (reserved_tokens >= 0),
    state TEXT NOT NULL DEFAULT 'reserved' CHECK(state IN ('reserved','confirmed','reversed')),
    PRIMARY KEY(tenant_id, request_id), FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);
'''


def connect(path: str | Path = ':memory:') -> sqlite3.Connection:
    db = sqlite3.connect(str(path), isolation_level=None)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript(SCHEMA)
    return db


def reserve(db: sqlite3.Connection, tenant_id: str, request_id: str, tokens: int) -> str:
    if not tenant_id or not request_id or not isinstance(tokens, int) or isinstance(tokens, bool) or not (1 <= tokens <= 1_000_000):
        return 'REJECTED_INPUT'
    db.execute('BEGIN IMMEDIATE')
    try:
        previous = db.execute('SELECT reserved_tokens, state FROM reservations WHERE tenant_id=? AND request_id=?',
                              (tenant_id, request_id)).fetchone()
        if previous:
            result = 'DUPLICATE' if previous[0] == tokens else 'REJECTED_IDEMPOTENCY'
        else:
            changed = db.execute('UPDATE tenants SET used_tokens = used_tokens + ? '
                                 'WHERE tenant_id=? AND used_tokens + ? <= monthly_token_limit',
                                 (tokens, tenant_id, tokens)).rowcount
            if changed:
                db.execute('INSERT INTO reservations (tenant_id, request_id, reserved_tokens) VALUES (?,?,?)',
                           (tenant_id, request_id, tokens))
                result = 'RESERVED'
            else:
                result = 'REJECTED_QUOTA'
        db.execute('COMMIT')
        return result
    except BaseException:
        db.execute('ROLLBACK')
        raise


def reverse(db: sqlite3.Connection, tenant_id: str, request_id: str) -> str:
    db.execute('BEGIN IMMEDIATE')
    try:
        record = db.execute('SELECT reserved_tokens, state FROM reservations WHERE tenant_id=? AND request_id=?',
                            (tenant_id, request_id)).fetchone()
        if record is None:
            outcome = 'NOT_FOUND'
        elif record[1] != 'reserved':
            outcome = 'UNCHANGED'
        else:
            db.execute("UPDATE reservations SET state='reversed' WHERE tenant_id=? AND request_id=?",
                       (tenant_id, request_id))
            db.execute('UPDATE tenants SET used_tokens=used_tokens-? WHERE tenant_id=?',
                       (record[0], tenant_id))
            outcome = 'REVERSED'
        db.execute('COMMIT')
        return outcome
    except BaseException:
        db.execute('ROLLBACK')
        raise


def verify_key(key: str, stored_digest: str) -> bool:
    if not isinstance(key, str) or not isinstance(stored_digest, str):
        return False
    actual = hashlib.sha256(key.encode('utf-8')).hexdigest()
    return hmac.compare_digest(actual, stored_digest)


if __name__ == '__main__':
    db = connect()
    db.execute('INSERT INTO tenants VALUES (?,?,?)', ('tenant_demo', 1000, 0))
    print(reserve(db, 'tenant_demo', 'req_001', 200))
    print(db.execute('SELECT tenant_id, used_tokens FROM tenants').fetchall())
