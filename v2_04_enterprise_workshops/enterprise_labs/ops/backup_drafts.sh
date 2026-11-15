#!/usr/bin/env bash
set -euo pipefail
source_dir="${1:?Provide draft directory}"
destination_dir="${2:?Provide protected backup directory}"
[[ -d "$source_dir" ]] || { echo 'Source does not exist' >&2; exit 2; }
mkdir -p -- "$destination_dir"
archive="$destination_dir/drafts-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
# Source directory must be a trusted local path; do not execute backup on user uploads.
tar -C "$(dirname "$source_dir")" -czf "$archive" -- "$(basename "$source_dir")"
sha256sum "$archive" > "$archive.sha256"
chmod 600 "$archive" "$archive.sha256"
echo "Backup created: $archive"
