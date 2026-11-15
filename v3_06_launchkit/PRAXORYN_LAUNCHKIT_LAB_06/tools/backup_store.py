#!/usr/bin/env python3
"""Create a consistent SQLite backup; verify integrity before restoration."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import sqlite3
import time


def backup(state: pathlib.Path, destination: pathlib.Path):
    source = state / "launchkit.db"
    if not source.is_file():
        raise FileNotFoundError("Initialize state before creating a backup")
    if destination.exists():
        raise FileExistsError("Destination backup must not exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError("Backup failed integrity_check")
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    meta = {"created_utc_epoch": int(time.time()), "sha256": checksum,
            "bytes": destination.stat().st_size, "integrity_check": "ok"}
    destination.with_suffix(".manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def inspect(path: pathlib.Path):
    manifest = json.loads(path.with_suffix(".manifest.json").read_text())
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    return {"valid": checksum == manifest["sha256"] and integrity == "ok",
            "integrity": integrity, "hash_matches": checksum == manifest["sha256"]}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create"); create.add_argument("state"); create.add_argument("destination")
    check = sub.add_parser("check"); check.add_argument("destination")
    args = p.parse_args()
    if args.cmd == "create":
        print(json.dumps(backup(pathlib.Path(args.state), pathlib.Path(args.destination))))
    else:
        print(json.dumps(inspect(pathlib.Path(args.destination))))

if __name__ == "__main__":
    main()
