"""Tenant-scoped queue and human review on SQLite for an offline lab."""
from __future__ import annotations
import sqlite3
from .core import utc_now

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS tenants (tenant_id TEXT PRIMARY KEY, credit INTEGER NOT NULL CHECK(credit >= 0));
CREATE TABLE IF NOT EXISTS jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
 kind TEXT NOT NULL CHECK(kind IN ('summary','reply')),
 input_text TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('queued','leased','pending_review','approved','rejected','failed')),
 draft TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 idempotency_key TEXT NOT NULL, UNIQUE(tenant_id,idempotency_key));
CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(state, id);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, job_id INTEGER,
 actor TEXT NOT NULL, event TEXT NOT NULL, occurred_at TEXT NOT NULL);
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    db.row_factory = sqlite3.Row
    return db


def init(db):
    db.executescript(SCHEMA)


def create_tenant(db, tenant_id: str, credit: int = 10):
    if not tenant_id.isascii() or not tenant_id.replace("-", "").replace("_", "").isalnum() or len(tenant_id) > 48 or len(tenant_id) < 2:
        raise ValueError("invalid tenant id")
    if credit < 0 or credit > 1000000:
        raise ValueError("invalid credit")
    db.execute("INSERT INTO tenants(tenant_id,credit) VALUES(?,?)", (tenant_id,credit))


def submit(db, tenant: str, kind: str, text: str, idem: str) -> int:
    if kind not in {"summary", "reply"} or not (1 <= len(text) <= 16000) or not (6 <= len(idem) <= 128):
        raise ValueError("Invalid job inputs")
    now = utc_now()
    db.execute("BEGIN IMMEDIATE")
    try:
        existing = db.execute("SELECT id FROM jobs WHERE tenant_id=? AND idempotency_key=?", (tenant,idem)).fetchone()
        if existing:
            db.execute("COMMIT")
            return int(existing["id"])
        changed = db.execute("UPDATE tenants SET credit=credit-1 WHERE tenant_id=? AND credit>0", (tenant,)).rowcount
        if changed != 1:
            raise ValueError("Tenant unknown or insufficient credit")
        cur = db.execute("INSERT INTO jobs(tenant_id,kind,input_text,state,created_at,updated_at,idempotency_key) VALUES(?,?,?,'queued',?,?,?)", (tenant,kind,text,now,now,idem))
        db.execute("INSERT INTO audit_events(tenant_id,job_id,actor,event,occurred_at) VALUES(?,?,'client','submitted',?)", (tenant,cur.lastrowid,now))
        db.execute("COMMIT")
        return int(cur.lastrowid)
    except Exception:
        db.execute("ROLLBACK")
        raise


def lease_one(db) -> dict | None:
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT id,tenant_id,kind,input_text FROM jobs WHERE state='queued' ORDER BY id LIMIT 1").fetchone()
        if not row:
            db.execute("COMMIT")
            return None
        db.execute("UPDATE jobs SET state='leased',updated_at=? WHERE id=? AND state='queued'", (utc_now(),row["id"]))
        db.execute("COMMIT")
        return dict(row)
    except Exception:
        db.execute("ROLLBACK")
        raise


def complete(db, job_id: int, draft: str, success=True) -> None:
    new_state = 'pending_review' if success else 'failed'
    if not isinstance(draft,str) or len(draft)>32000:
        raise ValueError("Invalid draft")
    db.execute("BEGIN IMMEDIATE")
    try:
        row=db.execute("SELECT tenant_id FROM jobs WHERE id=? AND state='leased'",(job_id,)).fetchone()
        if not row:raise ValueError("Job is not leased")
        db.execute("UPDATE jobs SET draft=?,state=?,updated_at=? WHERE id=?",(draft if success else None,new_state,utc_now(),job_id))
        if not success:
            db.execute("UPDATE tenants SET credit=credit+1 WHERE tenant_id=?",(row['tenant_id'],))
        db.execute("INSERT INTO audit_events(tenant_id,job_id,actor,event,occurred_at) VALUES(?,?,'worker',?,?)", (row['tenant_id'],job_id,new_state,utc_now()))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise


def decide(db, tenant: str, job_id: int, actor: str, approve: bool) -> None:
    if not actor or len(actor)>80:raise ValueError('Invalid reviewer')
    state='approved' if approve else 'rejected'
    db.execute("BEGIN IMMEDIATE")
    try:
        changed=db.execute("UPDATE jobs SET state=?,updated_at=? WHERE id=? AND tenant_id=? AND state='pending_review'",(state,utc_now(),job_id,tenant)).rowcount
        if changed != 1:raise ValueError('Job not found or not awaiting review')
        db.execute("INSERT INTO audit_events(tenant_id,job_id,actor,event,occurred_at) VALUES(?,?,?,?,?)",(tenant,job_id,actor,state,utc_now()))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise


def get_job(db, tenant: str, job_id: int) -> dict | None:
    row=db.execute("SELECT id,tenant_id,kind,state,draft,created_at,updated_at FROM jobs WHERE tenant_id=? AND id=?",(tenant,job_id)).fetchone()
    return dict(row) if row else None
