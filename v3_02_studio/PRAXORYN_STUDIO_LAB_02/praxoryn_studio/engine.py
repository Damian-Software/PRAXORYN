"""CLI-driven, SQLite-backed local work queue. Not a public SaaS backend."""
from __future__ import annotations
import json
import re
import sqlite3
import tempfile
import time
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from praxoryn_mediaops.pipeline import publish
from praxoryn_mediaops.verify import verify_manifest

TENANT_RE = re.compile(r"^[a-z][a-z0-9_-]{2,39}$")
JOB_RE = re.compile(r"^[0-9a-f]{32}$")
VALID_KINDS = {"internal", "marketing", "education", "report"}
DB_NAME = "studio.sqlite3"

class JobError(Exception):
    pass


def validate_tenant(value: str) -> str:
    if not isinstance(value, str) or not TENANT_RE.fullmatch(value):
        raise ValueError("tenant must match [a-z][a-z0-9_-]{2,39}")
    return value


def db_path(home: Path) -> Path:
    return home.resolve() / DB_NAME


def connect(home: Path) -> sqlite3.Connection:
    target = db_path(home)
    if not target.exists():
        raise FileNotFoundError("Run 'init' first")
    db = sqlite3.connect(target, timeout=10, isolation_level="DEFERRED")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    return db


@contextmanager
def session(home: Path):
    db = connect(home)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(home: Path) -> Path:
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    (home / "artifacts").mkdir(exist_ok=True, mode=0o700)
    (home / "exports").mkdir(exist_ok=True, mode=0o700)
    path = db_path(home)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS jobs (
               id TEXT PRIMARY KEY,
               tenant TEXT NOT NULL,
               kind TEXT NOT NULL,
               payload_json TEXT NOT NULL,
               status TEXT NOT NULL CHECK(status IN
                   ('queued','running','review','approved','exported','failed')),
               created_utc INTEGER NOT NULL,
               updated_utc INTEGER NOT NULL,
               attempts INTEGER NOT NULL DEFAULT 0,
               result_dir TEXT,
               error_code TEXT,
               reviewer TEXT,
               approved_utc INTEGER
            );
            CREATE INDEX IF NOT EXISTS ix_jobs_tenant_status
               ON jobs(tenant, status, created_utc);
            CREATE TABLE IF NOT EXISTS events (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               job_id TEXT NOT NULL REFERENCES jobs(id),
               at_utc INTEGER NOT NULL,
               event TEXT NOT NULL,
               actor TEXT NOT NULL,
               detail_code TEXT
            );
        """)
    finally:
        db.close()
    path.chmod(0o600)
    return path


def _now() -> int:
    return int(time.time())


def event(db: sqlite3.Connection, job_id: str, label: str,
          actor: str, code: str | None = None) -> None:
    db.execute("INSERT INTO events(job_id,at_utc,event,actor,detail_code) VALUES(?,?,?,?,?)",
               (job_id, _now(), label, actor, code))


def submit(home: Path, tenant: str, kind: str, prompt: str) -> str:
    tenant = validate_tenant(tenant)
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {sorted(VALID_KINDS)}")
    if not isinstance(prompt, str) or not (3 <= len(prompt.strip()) <= 4000):
        raise ValueError("prompt length must be 3..4000")
    job_id = uuid.uuid4().hex
    now = _now()
    payload = json.dumps({"prompt": prompt.strip()}, ensure_ascii=False)
    with session(home) as db:
        db.execute("INSERT INTO jobs(id,tenant,kind,payload_json,status,created_utc,updated_utc)"
                   " VALUES(?,?,?,?,?,?,?)", (job_id, tenant, kind, payload, 'queued', now, now))
        event(db, job_id, 'submitted', 'cli')
    return job_id


def _claim(db: sqlite3.Connection) -> dict | None:
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_utc,id LIMIT 1").fetchone()
        if row is None:
            db.execute('COMMIT')
            return None
        now = _now()
        db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated_utc=? "
                   "WHERE id=? AND status='queued'", (now, row['id']))
        event(db, row['id'], 'claimed', 'worker')
        db.execute('COMMIT')
        return dict(row)
    except Exception:
        db.execute('ROLLBACK')
        raise


def run_one(home: Path) -> str | None:
    db = connect(home)
    try:
        row = _claim(db)
        if row is None:
            return None
        job_id = row['id']
        # Use an opaque generated name; no user-controlled directory names.
        path = home.resolve() / 'artifacts' / job_id
        path.mkdir(mode=0o700, parents=False, exist_ok=False)
        payload = json.loads(row['payload_json'])
        brief = {'title': job_id, 'kind': row['kind'], 'prompt': payload['prompt']}
        with tempfile.TemporaryDirectory(prefix='prx-', dir=home.resolve()) as tmp:
            brief_path = Path(tmp) / 'brief.json'
            brief_path.write_text(json.dumps(brief), encoding='utf-8')
            try:
                result = publish(brief_path, path, live=False)
                problems = verify_manifest(result)
                if problems:
                    raise JobError('artifact-validation-failed')
            except Exception as exc:
                # Do not put the exception message, full path or input in persistent audit.
                code = type(exc).__name__[:60]
                with db:
                    db.execute("UPDATE jobs SET status='failed',error_code=?,updated_utc=? WHERE id=?",
                               (code, _now(), job_id))
                    event(db, job_id, 'failed', 'worker', code)
                raise
        # `result_dir` is an opaque ID, never a user path.
        with db:
            db.execute("UPDATE jobs SET status='review',result_dir=?,updated_utc=? WHERE id=?",
                       (job_id, _now(), job_id))
            event(db, job_id, 'awaiting_review', 'worker')
        return job_id
    finally:
        db.close()


def list_jobs(home: Path, tenant: str) -> list[dict[str, Any]]:
    tenant = validate_tenant(tenant)
    with session(home) as db:
        rows = db.execute("SELECT id,tenant,kind,status,created_utc,updated_utc,attempts,error_code "
                          "FROM jobs WHERE tenant=? ORDER BY created_utc DESC,id DESC LIMIT 100",
                          (tenant,)).fetchall()
        return [dict(x) for x in rows]


def get_job(home: Path, tenant: str, job_id: str) -> dict[str, Any]:
    tenant = validate_tenant(tenant)
    if not JOB_RE.fullmatch(job_id):
        raise ValueError('invalid job id')
    with session(home) as db:
        row = db.execute("SELECT id,tenant,kind,status,created_utc,updated_utc,attempts,error_code,reviewer "
                         "FROM jobs WHERE id=? AND tenant=?", (job_id, tenant)).fetchone()
        if not row:
            raise JobError('not found')
        return dict(row)


def approve(home: Path, tenant: str, job_id: str, reviewer: str) -> None:
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,64}', reviewer):
        raise ValueError('invalid reviewer ID')
    row = get_job(home, tenant, job_id)
    if row['status'] != 'review':
        raise JobError('job is not awaiting review')
    output = home.resolve() / 'artifacts' / job_id / job_id
    if verify_manifest(output):
        raise JobError('manifest verification failed')
    with session(home) as db:
        cur = db.execute("UPDATE jobs SET status='approved',reviewer=?,approved_utc=?,updated_utc=? "
                         "WHERE id=? AND tenant=? AND status='review'",
                         (reviewer, _now(), _now(), job_id, tenant))
        if cur.rowcount != 1:
            raise JobError('state changed; retry')
        event(db, job_id, 'approved', reviewer)


def export(home: Path, tenant: str, job_id: str) -> Path:
    row = get_job(home, tenant, job_id)
    if row['status'] not in ('approved', 'exported'):
        raise JobError('only approved jobs can be exported')
    folder = home.resolve() / 'artifacts' / job_id / job_id
    problems = verify_manifest(folder)
    if problems:
        raise JobError('manifest verification failed')
    dest = home.resolve() / 'exports' / f'{job_id}.zip'
    # Do not include internal SQLite event database or unapproved inputs.
    files = sorted(p for p in folder.iterdir() if p.is_file() and not p.is_symlink())
    for p in files:
        if p.stat().st_size > 50_000_000:
            raise JobError('artifact too large')
    temp = dest.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, arcname=p.name)
    temp.replace(dest)
    with session(home) as db:
        db.execute("UPDATE jobs SET status='exported',updated_utc=? WHERE id=? AND tenant=?",
                   (_now(), job_id, tenant))
        event(db, job_id, 'exported', 'cli')
    return dest


def doctor(home: Path) -> dict[str, Any]:
    import shutil
    return {
      'db_exists': db_path(home).is_file(),
      'ffmpeg': shutil.which('ffmpeg') is not None,
      'ffprobe': shutil.which('ffprobe') is not None,
      'libreoffice': shutil.which('libreoffice') is not None,
      'storage_path': str(home.resolve()),
    }
