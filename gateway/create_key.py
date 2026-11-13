import hashlib
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = os.getenv("LOCALAI_DB", "/var/lib/localai/state/gateway.sqlite3")
if len(sys.argv) != 3:
    raise SystemExit("Usage: create_key.py OWNER_ID DAILY_LIMIT")
owner = sys.argv[1]
limit = int(sys.argv[2])
if not owner or not (1 <= limit <= 100000):
    raise SystemExit("Invalid owner or daily limit")
Path(DB).parent.mkdir(parents=True, exist_ok=True)
key = "lai_" + secrets.token_urlsafe(32)
digest = hashlib.sha256(key.encode()).hexdigest()
with sqlite3.connect(DB) as db:
    db.execute("""CREATE TABLE IF NOT EXISTS api_keys (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      owner_id TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE,
      scopes TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
      expires_at TEXT, daily_limit INTEGER NOT NULL DEFAULT 100,
      created_at TEXT NOT NULL)""")
    db.execute("""INSERT INTO api_keys
      (owner_id,key_hash,scopes,enabled,expires_at,daily_limit,created_at)
      VALUES(?,?,?,1,NULL,?,?)""", (
          owner, digest, "models:read,chat:write", limit,
          datetime.now(timezone.utc).isoformat()
      ))
print("KEY_ONCE=", key)