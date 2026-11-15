"""Single-worker reference implementation: no customer data in audit entries."""
from __future__ import annotations
import json
import os
import sqlite3
import urllib.error
from pathlib import Path
from . import db
from .artifacts import save_result
from .security import Rejected
from .workflows import run


def process_one(state: Path, *, backend: str = "offline", config: dict | None = None) -> dict:
    conn = db.open_db(state)
    try:
        job = db.claim_one(conn)
        if not job:
            return {"processed": False}
        try:
            payload = json.loads(job["payload"])
            result = run(job["kind"], payload, backend=backend, config=config)
            relative_path = save_result(state, job["tenant"], job["id"], result)
            db.finish(conn, job, artifact=relative_path)
            return {"processed": True, "job_id": job["id"], "status": "review"}
        except (Rejected, ValueError, KeyError, TypeError, OSError, urllib.error.URLError,
                urllib.error.HTTPError, json.JSONDecodeError) as exc:
            # Operational logs record only error class and code, never payload or secrets.
            code = type(exc).__name__[:32]
            db.finish(conn, job, error_code=code)
            return {"processed": True, "job_id": job["id"], "status": "failed", "code": code}
    finally:
        conn.close()
