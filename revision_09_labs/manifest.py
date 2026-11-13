"""Small offline content manifest; not an atomic snapshot of live workloads."""
from pathlib import Path, PurePosixPath
import hashlib
import json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(directory: Path) -> dict[str, object]:
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Expected a real directory")
    entries = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symbolic links are not allowed")
        if path.is_file():
            rel = path.relative_to(directory).as_posix()
            entries[rel] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
    return {"algorithm": "sha256", "files": entries}


def verify_manifest(directory: Path, manifest: dict[str, object]) -> bool:
    directory = Path(directory)
    if manifest.get("algorithm") != "sha256" or not isinstance(manifest.get("files"), dict):
        return False
    for name, expected in manifest["files"].items():
        if not isinstance(name, str) or not isinstance(expected, dict):
            return False
        rel = PurePosixPath(name)
        if rel.is_absolute() or not rel.parts or any(p in {"", ".", ".."} for p in rel.parts):
            return False
        path = directory.joinpath(*rel.parts)
        if any(part.is_symlink() for part in [directory, *path.parents, path]):
            return False
        if not path.is_file() or path.stat().st_size != expected.get("bytes"):
            return False
        if _sha256(path) != expected.get("sha256"):
            return False
    return True


def manifest_json(directory: Path) -> str:
    return json.dumps(build_manifest(directory), indent=2, sort_keys=True) + "\n"
