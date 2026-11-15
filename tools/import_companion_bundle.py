#!/usr/bin/env python3
"""Import the book's verified companion archive without replacing existing files.

This is a local maintenance tool, not a production deployment utility.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

PREFIX = 'PRAXORYN_COMPLETE_COMPANION_SOURCES_EN/'


def safe_relative(path: str) -> Path:
    part = PurePosixPath(path)
    if not path or part.is_absolute() or '..' in part.parts or '\\' in path:
        raise ValueError(f'Unsafe archive path: {path!r}')
    return Path(*part.parts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='PRAXORYN_COMPLETE_COMPANION_SOURCES_EN.zip')
    parser.add_argument('--destination', type=Path, default=Path('companion-labs'))
    parser.add_argument('--apply', action='store_true', help='Write verified missing files; otherwise dry-run')
    args = parser.parse_args(argv)
    dest = args.destination.resolve()
    with zipfile.ZipFile(args.archive) as archive:
        manifest_path = PREFIX + 'MANIFEST.json'
        manifest = json.loads(archive.read(manifest_path))
        if not isinstance(manifest.get('files'), list) or manifest.get('lab_count') != 13:
            raise ValueError('Unsupported or incomplete source manifest')
        scanned = []
        for record in manifest['files']:
            relative = safe_relative(record['path'])
            archive_path = PREFIX + relative.as_posix()
            raw = archive.read(archive_path)
            digest = hashlib.sha256(raw).hexdigest()
            if digest != record['sha256']:
                raise ValueError('Hash mismatch: ' + archive_path)
            output = dest / relative
            if not output.resolve().is_relative_to(dest):
                raise ValueError('Destination escapes selected directory')
            if output.is_symlink() or any(x.is_symlink() for x in output.parents if x == dest or dest in x.parents):
                raise ValueError('Symlink in destination path')
            if output.exists() and output.read_bytes() != raw:
                raise FileExistsError(f'Conflicting file: {output} (no overwriting)')
            scanned.append((output, raw))
    pending = [(path, data) for path, data in scanned if not path.exists()]
    print(f'Validated {len(scanned)} files; missing {len(pending)}; existing {len(scanned)-len(pending)}')
    if not args.apply:
        print('Dry-run only. Use --apply to copy the missing files.')
        return 0
    for output, raw in pending:
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix='.staged-', dir=output.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, output)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    print(f'Imported {len(pending)} files into {dest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
