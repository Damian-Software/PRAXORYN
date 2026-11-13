"""Data objects and strict project-file traversal."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path

EXCLUDED = {'.git', '.venv', 'venv', '__pycache__', 'node_modules',
            'build', 'dist', '.idea', '.mypy_cache', '.ruff_cache', 'reports'}
EXTENSIONS = {'.py', '.cpp', '.cc', '.cxx', '.c', '.hpp', '.h', '.hh'}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    message: str
    source: str
    column: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


def project_files(root: Path, limit: int = 250, max_bytes: int = 128 * 1024) -> list[Path]:
    """Return small regular source files; never follow source symlinks."""
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Project path must be a directory')
    files = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(part in EXCLUDED or part.startswith('.') for part in rel.parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        if path.stat().st_size > max_bytes:
            continue
        files.append(path)
        if len(files) > limit:
            raise ValueError('Project file limit exceeded')
    return files


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root.resolve()).as_posix()
