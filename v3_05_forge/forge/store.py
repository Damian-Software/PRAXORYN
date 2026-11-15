"""Tenant-scoped SQLite queue and metadata-only audit log.

Lab implementation: one local worker. Review concurrency and retention before exposure.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY,
 tenant TEXT NOT NULL,
 kind TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN
  ('queued','processing','waiting_review','approved','rejected','failed')),
 idempotency_key TEXT NOT NULL,
 input_json TEXT NOT NULL,
 result_json TEXT,
 created_at INTEGER NOT NULL,
 updated_at INTEGER NOT NULL,
 UNIQUE(tenant,idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_jobs_state ON jobs(state,created_at);
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT,
 at INTEGER NOT NULL,
 tenant TEXT NOT NULL,
 job_id TEXT,
 event_type TEXT NOT NULL,
 details TEXT NOT NULL
);
'''


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=10000')
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript(SCHEMA)
    return con


def validate_tenant(value: str) -> str:
    if not value or len(value) > 40 or not all(c.isascii() and (c.isalnum() or c in '_-') for c in value):
        raise ValueError('Tenant must be 1-40 ASCII letters, digits, underscore or dash')
    return value


def audit(con, tenant: str, job_id: str | None, event: str, details: dict):
    # Store operational metadata, not document bodies or prompts.
    allowed = {'kind','state','reason_code','sha256','filename','status','backend'}
    filtered = {k: str(v)[:128] for k, v in details.items() if k in allowed}
    con.execute('INSERT INTO events (at,tenant,job_id,event_type,details) VALUES (?,?,?,?,?)',
                (int(time.time()), tenant, job_id, event, json.dumps(filtered, sort_keys=True)))


def submit(con, tenant: str, kind: str, payload: dict, idempotency_key: str) -> dict:
    tenant = validate_tenant(tenant)
    if len(idempotency_key) < 4 or len(idempotency_key) > 100:
        raise ValueError('Idempotency key length out of range')
    if kind not in {'invoice', 'code', 'brief', 'media_plan', 'evidence'}:
        raise ValueError('Unknown operation')
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(raw.encode('utf-8')) > 32_000:
        raise ValueError('Payload too large')
    now = int(time.time())
    con.execute('BEGIN IMMEDIATE')
    try:
        row = con.execute('SELECT * FROM jobs WHERE tenant=? AND idempotency_key=?',
                          (tenant, idempotency_key)).fetchone()
        if row:
            if row['kind'] != kind or row['input_json'] != raw:
                raise ValueError('Idempotency key is already bound to different input')
            con.execute('COMMIT')
            return dict(row)
        job_id = str(uuid.uuid4())
        con.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)',
                    (job_id, tenant, kind, 'queued', idempotency_key, raw, None, now, now))
        audit(con, tenant, job_id, 'job.submitted', {'kind':kind})
        con.execute('COMMIT')
        return dict(con.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone())
    except Exception:
        con.execute('ROLLBACK')
        raise


def get_job(con, tenant: str, job_id: str) -> dict:
    validate_tenant(tenant)
    row = con.execute('SELECT * FROM jobs WHERE tenant=? AND id=?',(tenant,job_id)).fetchone()
    if row is None:
        raise LookupError('Job not found in this tenant')
    return dict(row)


def claim(con):
    con.execute('BEGIN IMMEDIATE')
    try:
        row = con.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created_at,id LIMIT 1").fetchone()
        if not row:
            con.execute('COMMIT')
            return None
        now = int(time.time())
        con.execute("UPDATE jobs SET state='processing',updated_at=? WHERE id=? AND state='queued'",(now,row['id']))
        audit(con,row['tenant'],row['id'],'job.claimed',{'state':'processing'})
        con.execute('COMMIT')
        return dict(row)
    except Exception:
        con.execute('ROLLBACK')
        raise


def complete(con, tenant: str, job_id: str, result: dict, state: str):
    if state not in ('waiting_review','failed'):
        raise ValueError('Worker cannot directly approve work')
    con.execute('BEGIN IMMEDIATE')
    try:
        row = get_job(con,tenant,job_id)
        if row['state'] != 'processing':
            raise ValueError('Invalid worker transition')
        con.execute('UPDATE jobs SET state=?,result_json=?,updated_at=? WHERE tenant=? AND id=?',
                    (state,json.dumps(result,sort_keys=True),int(time.time()),tenant,job_id))
        audit(con,tenant,job_id,'job.completed',{'state':state})
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK')
        raise


def review(con, tenant: str, job_id: str, decision: str, reviewer: str):
    if decision not in ('approved','rejected'):
        raise ValueError('Decision must be approved or rejected')
    if not reviewer or len(reviewer)>64:
        raise ValueError('Reviewer identifier required')
    con.execute('BEGIN IMMEDIATE')
    try:
        row = get_job(con,tenant,job_id)
        if row['state']!='waiting_review':
            raise ValueError('Only waiting_review can be reviewed')
        con.execute('UPDATE jobs SET state=?,updated_at=? WHERE tenant=? AND id=?',
                    (decision,int(time.time()),tenant,job_id))
        audit(con,tenant,job_id,'job.reviewed',{'state':decision})
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK')
        raise


def events(con, tenant: str, limit: int=50):
    validate_tenant(tenant)
    return [dict(x) for x in con.execute('SELECT at,job_id,event_type,details FROM events WHERE tenant=? ORDER BY seq DESC LIMIT ?',
                                         (tenant,min(max(limit,1),100)))]
