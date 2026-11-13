#!/usr/bin/env bash
set -euo pipefail
: "${OPSBRIDGE_HOME:?Set OPSBRIDGE_HOME}"
: "${BACKUP_DIR:?Set BACKUP_DIR}"
mkdir -p -- "$BACKUP_DIR"
chmod 700 -- "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
# sqlite3 .backup creates a consistent snapshot even when WAL is enabled.
sqlite3 "$OPSBRIDGE_HOME/opsbridge.sqlite" ".backup '$BACKUP_DIR/opsbridge-$stamp.sqlite'"
chmod 600 "$BACKUP_DIR/opsbridge-$stamp.sqlite"
sha256sum "$BACKUP_DIR/opsbridge-$stamp.sqlite" > "$BACKUP_DIR/opsbridge-$stamp.sha256"
# Back up private artifacts separately, encrypted under your organization's policy.
echo "Database snapshot created; private artifacts are NOT included."
