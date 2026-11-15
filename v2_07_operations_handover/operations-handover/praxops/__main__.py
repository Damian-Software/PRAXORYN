"""Run: python3 -m praxops --help"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from . import client
from . import diagnostics
from . import metadata


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record(path: Path, action: str, status: str, elapsed: int, model: str = "local-model") -> None:
    metadata.append(path, {"timestamp": utc_now(), "operation": action, "status": status, "latency_ms": int(elapsed), "model_tag": model[:50]})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Local AI operational laboratory; loopback endpoints only")
    p.add_argument("--url", default=os.environ.get("PRAXOPS_URL", "http://127.0.0.1:8080"))
    p.add_argument("--model", default=os.environ.get("PRAXOPS_MODEL", "mock-model"))
    p.add_argument("--log", type=Path, default=Path("./private/probes.jsonl"))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    sub.add_parser("models")
    probe = sub.add_parser("probe"); probe.add_argument("--count", type=int, default=3)
    sub.add_parser("report")
    r = sub.add_parser("retain"); r.add_argument("--days", type=int, default=14)
    g = sub.add_parser("gate"); g.add_argument("--min-samples", type=int, default=5); g.add_argument("--max-error-rate", type=float, default=0.1); g.add_argument("--max-p95-ms", type=int, default=5000)
    args = p.parse_args(argv)
    if args.command == "report":
        print(json.dumps(diagnostics.report(args.log), indent=2)); return 0
    if args.command == "retain":
        before, after = metadata.retain(args.log, args.days)
        print(json.dumps({"previous": before, "retained": after})); return 0
    if args.command == "gate":
        if args.min_samples <= 0 or not 0 <= args.max_error_rate <= 1 or args.max_p95_ms <= 0:
            raise ValueError("Invalid gate thresholds")
        ok, reasons = diagnostics.gate(args.log, args.min_samples, args.max_error_rate, args.max_p95_ms)
        print(json.dumps({"pass": ok, "reasons": reasons})); return 0 if ok else 2
    client.safe_base(args.url)
    if args.command == "health":
        result = client.health(args.url)
        print(json.dumps(result)); return 0 if result["ok"] else 2
    if args.command == "models":
        print(json.dumps({"model_ids": client.models(args.url)})); return 0
    if args.command == "probe":
        if not 1 <= args.count <= 50:
            raise ValueError("count must be 1..50")
        failures = 0
        for _ in range(args.count):
            try:
                duration, answer = client.chat(args.url, args.model, "Reply with the word READY.")
                status = "ok" if answer.strip() else "invalid"
            except client.ApiError as exc:
                duration = 0
                status = "unavailable" if exc.status in (429, 503) else "transport" if exc.status == 0 else "invalid"
            record(args.log, "synthetic_probe", status, duration, args.model)
            failures += status != "ok"
            print(json.dumps({"status": status, "latency_ms": duration}))
        return 2 if failures else 0
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, client.ApiError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
