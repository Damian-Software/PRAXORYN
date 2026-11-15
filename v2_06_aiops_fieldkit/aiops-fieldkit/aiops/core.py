"""Common file handling and audit metadata. No prompts in logs."""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
import pathlib
import tempfile
from datetime import datetime, timezone

MAX_FILE_BYTES = 2_000_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_workspace_file(root: str, relative_path: str, allowed_suffixes=(".txt", ".csv")) -> tuple[bytes, str]:
    base = pathlib.Path(root).resolve(strict=True)
    name = pathlib.PurePosixPath(relative_path)
    if name.is_absolute() or ".." in name.parts or name.suffix.lower() not in allowed_suffixes:
        raise ValueError("File path or type is not allowed")
    target = base.joinpath(*name.parts)
    if target.is_symlink() or any(p.is_symlink() for p in [*target.parents][:len(target.parents)] if base in p.parents or p == base):
        raise ValueError("Symlinks are not allowed")
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise ValueError("File is outside workspace")
    if resolved.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("File exceeds size limit")
    with resolved.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("File exceeds size limit")
    data.decode("utf-8-sig")
    return data, sha256_bytes(data)


def safe_write(path: str, content: bytes):
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".staged-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def is_public_address(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def json_record(**values) -> str:
    return json.dumps({"at": utc_now(), **values}, ensure_ascii=True, separators=(",", ":"))
