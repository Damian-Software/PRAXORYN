"""Offline-first job queue and minimal audit trail for educational deployments.

Important: this is a single-machine reference, NOT a public multi-tenant SaaS.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

KINDS = frozenset({'summary', 'code_review', 'document', 'image'})
TENANT_RE = re.compile(r'^[a-z][a-z0-9_-]{2,31}$')
MAX_PAYLOAD_BYTES = 24 * 1024


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clean_tenant(value):
    if not isinstance(value, str) or not TENANT_RE.fullmatch(value):
        raise ValueError('tenant must match [a-z][a-z0-9_-]{2,31}')
    return value


def bounded_json(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError('request payload exceeds 24 KiB')
    return raw.decode('utf-8')


def path_under(root, *parts):
    root = Path(root).resolve()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError('path escapes private root')
    return path


def open_db(root):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    db_path = root / 'opsbridge.sqlite'
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout=10000')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        tenant TEXT NOT NULL,
        kind TEXT NOT NULL,
        state TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        lease_until INTEGER NOT NULL DEFAULT 0,
        output_path TEXT,
        error_code TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state, lease_until, created_at);
    CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant, created_at);
    CREATE TABLE IF NOT EXISTS audit (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        at TEXT NOT NULL,
        actor TEXT NOT NULL,
        job_id TEXT,
        event TEXT NOT NULL,
        detail_code TEXT NOT NULL,
        previous_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL
    );
    ''')
    os.chmod(db_path, 0o600)
    return conn


def audit_event(db, actor, job_id, event, detail_code='ok'):
    # Never put prompts, customer documents, secrets, or token values in audit rows.
    prev = db.execute('SELECT event_hash FROM audit ORDER BY event_id DESC LIMIT 1').fetchone()
    previous_hash = prev['event_hash'] if prev else '0' * 64
    fields = [utc_now(), actor, job_id or '', event, detail_code, previous_hash]
    raw = json.dumps(fields, separators=(',', ':'), ensure_ascii=False)
    event_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    db.execute('''INSERT INTO audit(at,actor,job_id,event,detail_code,previous_hash,event_hash)
                  VALUES (?,?,?,?,?,?,?)''', (*fields[:2], job_id, event, detail_code, previous_hash, event_hash))
    return event_hash


def verify_audit(db):
    prev = '0' * 64
    for row in db.execute('SELECT * FROM audit ORDER BY event_id'):
        raw = json.dumps([row['at'], row['actor'], row['job_id'] or '', row['event'],
                          row['detail_code'], row['previous_hash']], separators=(',', ':'), ensure_ascii=False)
        expected = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        if not (hmac.compare_digest(row['previous_hash'], prev)
                and hmac.compare_digest(row['event_hash'], expected)):
            return False, row['event_id']
        prev = expected
    return True, None


def create_job(db, tenant, kind, payload):
    tenant = clean_tenant(tenant)
    if kind not in KINDS:
        raise ValueError(f'unsupported kind: {kind}')
    payload_json = bounded_json(payload)
    job_id = secrets.token_hex(12)
    now = utc_now()
    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute('''INSERT INTO jobs(job_id,tenant,kind,state,payload_json,created_at,updated_at)
                      VALUES (?,?,?,\'queued\',?,?,?)''', (job_id, tenant, kind, payload_json, now, now))
        audit_event(db, 'cli', job_id, 'job_queued')
        db.commit()
    except Exception:
        db.rollback()
        raise
    return job_id


def claim_job(db, lease_seconds=120):
    # Single-host SQLite queue. A lease is reclaimed after timeout; effects must be idempotent.
    now = int(time.time())
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute('''SELECT * FROM jobs WHERE state='queued' OR
                            (state='running' AND lease_until<?)
                            ORDER BY created_at, job_id LIMIT 1''', (now,)).fetchone()
        if row is None:
            db.commit()
            return None
        db.execute('''UPDATE jobs SET state='running', attempts=attempts+1,
                      lease_until=?, updated_at=? WHERE job_id=?''',
                   (now+lease_seconds, utc_now(), row['job_id']))
        audit_event(db, 'worker', row['job_id'], 'job_claimed', 'lease_started')
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


def complete_job(db, job_id, result_path=None, error_code=None):
    db.execute('BEGIN IMMEDIATE')
    try:
        state = 'review' if error_code is None else 'failed'
        cur = db.execute('''UPDATE jobs SET state=?, output_path=?, error_code=?,
                            lease_until=0, updated_at=? WHERE job_id=? AND state='running' ''',
                         (state, str(result_path) if result_path else None, error_code, utc_now(), job_id))
        if cur.rowcount != 1:
            raise ValueError('job is not in running state')
        audit_event(db, 'worker', job_id, 'job_finished', 'ok' if error_code is None else error_code)
        db.commit()
    except Exception:
        db.rollback()
        raise


def transition(db, job_id, from_state, to_state, actor):
    allowed = {('review','approved'), ('approved','released'), ('review','rejected')}
    if (from_state, to_state) not in allowed:
        raise ValueError('invalid transition')
    db.execute('BEGIN IMMEDIATE')
    try:
        cur = db.execute('UPDATE jobs SET state=?, updated_at=? WHERE job_id=? AND state=?',
                         (to_state, utc_now(), job_id, from_state))
        if cur.rowcount != 1:
            raise ValueError('wrong current state or unknown job')
        audit_event(db, actor, job_id, f'job_{to_state}')
        db.commit()
    except Exception:
        db.rollback()
        raise


def list_jobs(db, tenant):
    clean_tenant(tenant)
    return [dict(row) for row in db.execute('''SELECT job_id,tenant,kind,state,created_at,
                            updated_at,attempts,error_code FROM jobs WHERE tenant=?
                            ORDER BY created_at DESC, job_id DESC LIMIT 100''', (tenant,))]
