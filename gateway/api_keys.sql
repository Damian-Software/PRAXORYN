CREATE TABLE IF NOT EXISTS api_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  scopes TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  expires_at TEXT,
  daily_limit INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_daily (
  key_id INTEGER NOT NULL,
  day_utc TEXT NOT NULL,
  requests INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (key_id, day_utc),
  FOREIGN KEY (key_id) REFERENCES api_keys(id)
);
CREATE INDEX IF NOT EXISTS idx_keys_owner ON api_keys(owner_id);
