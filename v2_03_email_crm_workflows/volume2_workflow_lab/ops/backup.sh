#!/usr/bin/env bash
set -euo pipefail
: "${LOCALAI_DB:=./state/workflow.sqlite3}"
: "${LOCALAI_BACKUP_DIR:=./backups}"
mkdir -p "$LOCALAI_BACKUP_DIR"
chmod 0700 "$LOCALAI_BACKUP_DIR"
python3 - "$LOCALAI_DB" "$LOCALAI_BACKUP_DIR" <<'PY'
import sqlite3, sys, datetime
from pathlib import Path
source = Path(sys.argv[1]); directory = Path(sys.argv[2])
if not source.is_file():
    raise SystemExit('Database does not exist')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
target = directory / f'workflow-{stamp}.sqlite3'
src = sqlite3.connect(source)
dst = sqlite3.connect(target)
try:
    src.backup(dst)
    if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise SystemExit('Backup integrity check failed')
finally:
    dst.close(); src.close()
target.chmod(0o600)
print('Verified backup:', target)
PY
