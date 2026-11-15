#!/usr/bin/env python3
"""Fixed-command Ruff/clang-tidy integration; never execute submitted code."""
from __future__ import annotations
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

ALLOWED = {".py", ".cpp", ".cc", ".cxx", ".h", ".hpp"}


def analyze(path: pathlib.Path, *, timeout: int = 30) -> dict:
    root = path.resolve()
    if not root.is_file() or root.suffix.lower() not in ALLOWED:
        raise ValueError("Only a local source file with a supported suffix can be analyzed")
    if root.stat().st_size > 256_000:
        raise ValueError("Source file is too large")
    if root.suffix == ".py":
        cmd = ["ruff", "check", "--output-format", "json", "--no-cache", str(root)]
    else:
        # C++ analysis needs compile_commands.json from a trusted CMake build.
        database = root.parent / "compile_commands.json"
        if not database.is_file():
            return {"status": "needs_compilation_database", "file": root.name,
                    "hint": "cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"}
        cmd = ["clang-tidy", str(root), "-p", str(root.parent)]
    if shutil.which(cmd[0]) is None:
        return {"status": "tool_missing", "tool": cmd[0], "file": root.name}
    try:
        process = subprocess.run(cmd, cwd=root.parent, capture_output=True, text=True,
                                 timeout=timeout, check=False, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": cmd[0], "seconds": timeout}
    return {"status": "completed", "tool": cmd[0], "exit_code": process.returncode,
            "stdout": process.stdout[:100000], "stderr": process.stderr[:20000]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file"); p.add_argument("--json-out")
    args = p.parse_args()
    result = analyze(pathlib.Path(args.file))
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        pathlib.Path(args.json_out).write_text(output + "\n")
    print(output)
    # Findings are reported by the tool's exit code and reviewed by a person.
    return 0 if result.get("status") == "completed" and result.get("exit_code") == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
