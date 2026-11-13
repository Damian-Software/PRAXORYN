"""SQLite-backed teaching queue: one worker, explicit states, tenant filters."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from .security import Rejected, slug, safe_json, key_digest, make_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    digest TEXT PRIMARY KEY, tenant TEXT NOT NULL,
    scope TEXT NOT NULL CHECK(scope IN ('read','submit','approve','admin')),
    label TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, tenant TEXT NOT NULL,
    kind TEXT NOT NULL, payload TEXT NOT NULL,
    idem_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN
       ('queued','running','review','approved','failed')),
    created_at INTEGER NOT NULL, changed_at INTEGER NOT NULL,
    artifact TEXT NOT NULL DEFAULT '', error_code TEXT NOT NULL DEFAULT '',
    reviewer TEXT NOT NULL DEFAULT '', UNIQUE(tenant, idem_key)
);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status ON jobs(tenant,status);
CREATE TABLE IF NOT EXISTS audit (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL,
    tenant TEXT NOT NULL, action TEXT NOT NULL, subject TEXT NOT NULL,
    previous TEXT NOT NULL, digest TEXT NOT NULL
);
"""


def open_db(state: Path) -> sqlite3.Connection:
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    dbfile = state / "launchkit.db"
    connection = sqlite3.connect(dbfile, timeout=12, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=12000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(SCHEMA)
    if dbfile.exists():
        dbfile.chmod(0o600)
    return connection


def log(conn: sqlite3.Connection, tenant: str, action: str, subject: str) -> None:
    # A local hash chain is tamper-evident only when a trusted checkpoint is
    # regularly exported and stored beyond this filesystem.
    latest = conn.execute("SELECT digest FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
    previous = latest["digest"] if latest else "0" * 64
    stamp = int(time.time())
    data = f"{previous}|{stamp}|{tenant}|{action}|{subject}".encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    conn.execute("INSERT INTO audit(at,tenant,action,subject,previous,digest) VALUES(?,?,?,?,?,?)",
                 (stamp, tenant, action, subject, previous, digest))


def create_client(conn, tenant: str, scope: str, label: str) -> str:
    slug(tenant, "tenant")
    if scope not in {"read", "submit", "approve", "admin"}:
        raise Rejected("Unsupported scope")
    slug(label, "label")
    secret = make_key()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("INSERT INTO clients(digest,tenant,scope,label,created_at) VALUES(?,?,?,?,?)",
                     (key_digest(secret), tenant, scope, label, int(time.time())))
        log(conn, tenant, "key_issued", label)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return secret


def authenticate(conn, token: str):
    from .security import key_digest
    try:
        digest = key_digest(token)
    except (Rejected, UnicodeEncodeError):
        return None
    row = conn.execute("SELECT tenant,scope,label FROM clients WHERE digest=? AND enabled=1", (digest,)).fetchone()
    return dict(row) if row else None


def submit(conn, tenant: str, kind: str, payload: dict, idem: str) -> tuple[str, bool]:
    slug(tenant, "tenant"); slug(kind, "workflow"); slug(idem, "idempotency key")
    content = safe_json(payload)
    fingerprint = hashlib.sha256((kind + "\n" + content).encode()).hexdigest()
    now = int(time.time())
    conn.execute("BEGIN IMMEDIATE")
    try:
        prior = conn.execute("SELECT id,payload_hash FROM jobs WHERE tenant=? AND idem_key=?",
                             (tenant, idem)).fetchone()
        if prior:
            if prior["payload_hash"] != fingerprint:
                raise Rejected("Idempotency key reused with different content")
            conn.execute("COMMIT")
            return prior["id"], False
        identifier = uuid.uuid4().hex
        conn.execute("INSERT INTO jobs(id,tenant,kind,payload,idem_key,payload_hash,status,created_at,changed_at) "
                     "VALUES(?,?,?,?,?,?,'queued',?,?)",
                     (identifier, tenant, kind, content, idem, fingerprint, now, now))
        log(conn, tenant, "submitted", identifier)
        conn.execute("COMMIT")
        return identifier, True
    except Exception:
        conn.execute("ROLLBACK")
        raise


def get_job(conn, tenant: str, identifier: str) -> dict | None:
    row = conn.execute("SELECT id,tenant,kind,status,created_at,changed_at,artifact,error_code,reviewer "
                       "FROM jobs WHERE id=? AND tenant=?", (identifier, tenant)).fetchone()
    return dict(row) if row else None


def list_jobs(conn, tenant: str, limit: int = 30) -> list[dict]:
    rows = conn.execute("SELECT id,kind,status,changed_at,artifact FROM jobs WHERE tenant=? "
                        "ORDER BY changed_at DESC LIMIT ?", (tenant, min(limit, 100))).fetchall()
    return [dict(row) for row in rows]


def claim_one(conn) -> dict | None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT id,tenant,kind,payload FROM jobs WHERE status='queued' "
                           "ORDER BY created_at,id LIMIT 1").fetchone()
        if not row:
            conn.execute("COMMIT")
            return None
        conn.execute("UPDATE jobs SET status='running',changed_at=? WHERE id=? AND status='queued'",
                     (int(time.time()), row["id"]))
        log(conn, row["tenant"], "claimed", row["id"])
        conn.execute("COMMIT")
        return dict(row)
    except Exception:
        conn.execute("ROLLBACK")
        raise


def finish(conn, item: dict, artifact: str = "", error_code: str = "") -> None:
    if bool(artifact) == bool(error_code):
        raise Rejected("Provide exactly one outcome")
    state = "review" if artifact else "failed"
    conn.execute("BEGIN IMMEDIATE")
    try:
        updated = conn.execute("UPDATE jobs SET status=?,artifact=?,error_code=?,changed_at=? "
                               "WHERE id=? AND tenant=? AND status='running'",
                               (state, artifact, error_code, int(time.time()), item["id"], item["tenant"]))
        if updated.rowcount != 1:
            raise Rejected("Invalid worker state transition")
        log(conn, item["tenant"], state, item["id"])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def approve(conn, tenant: str, identifier: str, reviewer: str) -> None:
    slug(reviewer, "reviewer")
    conn.execute("BEGIN IMMEDIATE")
    try:
        changed = conn.execute("UPDATE jobs SET status='approved',reviewer=?,changed_at=? "
                               "WHERE id=? AND tenant=? AND status='review'",
                               (reviewer, int(time.time()), identifier, tenant))
        if changed.rowcount != 1:
            raise Rejected("Job cannot be approved in its current state")
        log(conn, tenant, "approved", identifier)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def audit_health(conn) -> tuple[bool, str]:
    prev = "0" * 64
    for row in conn.execute("SELECT at,tenant,action,subject,previous,digest FROM audit ORDER BY seq"):
        material = f"{prev}|{row['at']}|{row['tenant']}|{row['action']}|{row['subject']}".encode()
        calculated = hashlib.sha256(material).hexdigest()
        if row["previous"] != prev or calculated != row["digest"]:
            return False, "broken_chain"
        prev = row["digest"]
    return True, prev
