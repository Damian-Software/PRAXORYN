#!/usr/bin/env bash
set -euo pipefail
# Backup is sensitive: include only the necessary workspace, with restricted permissions.
WORKSPACE="${1:-/var/lib/praxoryn/mediaops}"
DEST="${2:-$HOME/praxoryn-backup.tar.gz}"
umask 077
tar --create --gzip --file "$DEST" --directory "$(dirname "$WORKSPACE")" "$(basename "$WORKSPACE")"
printf 'Backup written: %s\n' "$DEST"
