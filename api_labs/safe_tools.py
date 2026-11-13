"""LAB: allowlisted, read-only diagnostics. No model-controlled shell execution.

This module intentionally does NOT expose a generic 'command' argument.
A production agent needs additional isolation, authorization and review.
"""
from __future__ import annotations

import subprocess
from typing import Any

COMMANDS: dict[str, tuple[str, ...]] = {
    "kernel": ("/usr/bin/uname", "-r"),
    "identity": ("/usr/bin/id", "-u"),
    "disk": ("/usr/bin/df", "-h", "/"),
}
ENV = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}


def run_diagnostic(action: str) -> dict[str, Any]:
    """Only a fixed operation name is accepted. Never accepts shell text."""
    if action not in COMMANDS:
        return {"ok": False, "status": 403, "error": "action_denied"}
    try:
        result = subprocess.run(
            list(COMMANDS[action]),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            shell=False,
            env=ENV,
            cwd="/",
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": 504, "error": "diagnostic_timeout"}
    except OSError:
        return {"ok": False, "status": 503, "error": "diagnostic_unavailable"}
    return {
        "ok": result.returncode == 0,
        "status": 200 if result.returncode == 0 else 502,
        "returncode": result.returncode,
        "output": result.stdout[:4096],
        "truncated": len(result.stdout) > 4096,
    }


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="LAB read-only diagnostic tool")
    parser.add_argument("action", help="one of: " + ", ".join(COMMANDS))
    args = parser.parse_args()
    print(json.dumps(run_diagnostic(args.action), ensure_ascii=False))
