"""Check an artifact hash from its own directory without trusting absolute paths."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def verify(manifest_file):
    manifest_file=Path(manifest_file).resolve()
    rec=json.loads(manifest_file.read_text(encoding='utf-8'))
    name=rec['artifact']
    if Path(name).name != name or name in ('.','..'):
        raise ValueError('manifest artifact must be a bare file name')
    path=manifest_file.parent/name
    if path.is_symlink():raise ValueError('symlink not allowed')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    return digest==rec['sha256']


def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');args=p.parse_args()
    ok=verify(args.manifest);print('ok' if ok else 'mismatch')
    raise SystemExit(0 if ok else 2)

if __name__=='__main__':main()
