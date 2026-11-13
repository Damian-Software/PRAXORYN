#!/usr/bin/env bash
set -Eeuo pipefail
: "${STUDIO_HOME:?Set STUDIO_HOME to the private data directory}"
: "${BACKUP_DIR:?Set BACKUP_DIR to the backup destination}"
umask 077
mkdir -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
# Stop job writers or take a coordinated backup before archiving artifact directories.
python3 - "$STUDIO_HOME" "$BACKUP_DIR/$STAMP.sqlite3" <<'PY'
from pathlib import Path
import sqlite3,sys
src=sqlite3.connect(Path(sys.argv[1])/'studio.sqlite3')
dst=sqlite3.connect(sys.argv[2])
with dst: src.backup(dst)
dst.close();src.close()
PY
sha256sum "$BACKUP_DIR/$STAMP.sqlite3" > "$BACKUP_DIR/$STAMP.sqlite3.sha256"
printf 'Database snapshot saved; artifact files require a coordinated separate backup.\n'
