#!/usr/bin/env python3
"""Hash an existing regular file. This does not attest safety or authorship."""
import argparse
import hashlib
import json
from pathlib import Path


def describe_file(file: Path) -> dict:
    if not file.is_file() or file.is_symlink():
        raise ValueError('Expected a regular file, not a symlink')
    h = hashlib.sha256()
    size = 0
    with file.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            size += len(chunk)
            h.update(chunk)
    return {'file_name': file.name, 'size_bytes': size, 'sha256': h.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    print(json.dumps(describe_file(args.file), indent=2))


if __name__ == '__main__':
    main()
