"""Constrained local file handling for staged synthetic examples."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path

MAX_INPUT_BYTES = 2 * 1024 * 1024
ALLOWED_SUFFIXES = {'.csv','.py','.cpp','.h','.hpp','.txt','.md','.json'}


def checked_input(root: Path, name: str) -> Path:
    if not name or '/' in name or '\\' in name or name.startswith('.'):
        raise ValueError('Use a simple filename in the configured input directory')
    p = root / name
    if p.is_symlink() or not p.is_file():
        raise ValueError('Missing input or symbolic link rejected')
    if p.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError('Unsupported input extension')
    if p.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError('Input exceeds 2 MiB laboratory limit')
    return p


def digest_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(65536),b''):
            h.update(chunk)
    return h.hexdigest()


def safe_output_dir(root: Path, job_id: str) -> Path:
    import uuid
    canonical = str(uuid.UUID(job_id))
    p=root/canonical
    p.mkdir(parents=True,exist_ok=True,mode=0o700)
    if p.is_symlink():raise ValueError('Output folder is a symlink')
    os.chmod(p,0o700)
    return p


def write_private(path: Path, data: bytes):
    import os
    if path.is_symlink():raise ValueError('Refusing symlink output')
    fd=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(data)
