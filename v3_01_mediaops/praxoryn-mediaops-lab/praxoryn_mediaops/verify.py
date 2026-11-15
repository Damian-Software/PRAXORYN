"""Validate a single lab manifest and generated artefacts."""
from pathlib import Path
import json
import hashlib

ALLOWED={'draft.txt','preview.png','report.docx','report.pdf','still-preview.mp4'}

def verify_manifest(folder: Path) -> list[str]:
    folder=folder.resolve()
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    errors=[]
    for entry in manifest['artifacts']:
        name=entry.get('file','')
        if '/' in name or '\\' in name or not name or name in ('.','..'):
            errors.append('unsafe file name'); continue
        path=folder/name
        if path.is_symlink() or not path.is_file():
            errors.append(f'missing or symlink: {name}'); continue
        if path.stat().st_size != entry['bytes']:
            errors.append(f'wrong size: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            errors.append(f'wrong digest: {name}')
    return errors
