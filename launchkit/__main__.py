"""LaunchKit CLI: setup, keys, worker, inspection and local API."""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from . import db
from .api import serve
from .artifacts import verify_result
from .security import Rejected, prepare_private_dir
from .worker import process_one


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Praxoryn LaunchKit")
    parser.add_argument("--state", default="./private-state", help="Private state directory")
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("init")
    issue = command.add_parser("issue-key")
    issue.add_argument("--tenant", required=True)
    issue.add_argument("--scope", required=True, choices=["read", "submit", "approve", "admin"])
    issue.add_argument("--label", required=True)
    submit = command.add_parser("submit")
    submit.add_argument("--tenant", required=True)
    submit.add_argument("--kind", required=True)
    submit.add_argument("--payload", required=True)
    submit.add_argument("--key", required=True)
    worker = command.add_parser("work-once")
    worker.add_argument("--backend", choices=["offline", "local"], default="offline")
    worker.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    worker.add_argument("--model", default="local-model")
    status = command.add_parser("show")
    status.add_argument("--tenant", required=True)
    status.add_argument("--id", required=True)
    approve = command.add_parser("approve")
    approve.add_argument("--tenant", required=True)
    approve.add_argument("--id", required=True)
    approve.add_argument("--reviewer", required=True)
    verify = command.add_parser("verify")
    verify.add_argument("--tenant", required=True)
    verify.add_argument("--id", required=True)
    command.add_parser("audit-check")
    server = command.add_parser("serve")
    server.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    try:
        state = prepare_private_dir(Path(args.state))
        if args.command == "init":
            db.open_db(state).close()
            print(json.dumps({"status": "initialized", "state": str(state)}))
        elif args.command == "issue-key":
            with db.open_db(state) as conn:
                secret = db.create_client(conn, args.tenant, args.scope, args.label)
            print(secret, file=sys.stdout)   # Capture to a protected file, never a ticket or chat.
        elif args.command == "submit":
            content = json.loads(Path(args.payload).read_text(encoding="utf-8"))
            with db.open_db(state) as conn:
                identifier, created = db.submit(conn, args.tenant, args.kind, content, args.key)
            print(json.dumps({"job_id": identifier, "created": created}))
        elif args.command == "work-once":
            token = ""
            credential_dir = os.environ.get("CREDENTIALS_DIRECTORY", "")
            if credential_dir:
                token_file = Path(credential_dir) / "model_api_key"
                if token_file.is_file():
                    token = token_file.read_text().strip()
            result = process_one(state, backend=args.backend,
                                 config={"endpoint": args.endpoint, "model": args.model, "api_key": token})
            print(json.dumps(result))
        elif args.command == "show":
            with db.open_db(state) as conn:
                item = db.get_job(conn, args.tenant, args.id)
            print(json.dumps(item, ensure_ascii=False))
        elif args.command == "approve":
            with db.open_db(state) as conn:
                db.approve(conn, args.tenant, args.id, args.reviewer)
            print("approved")
        elif args.command == "verify":
            print(json.dumps({"valid": verify_result(state, args.tenant, args.id)}))
        elif args.command == "audit-check":
            with db.open_db(state) as conn:
                good, tip = db.audit_health(conn)
            print(json.dumps({"valid": good, "tip": tip}))
            return 0 if good else 2
        elif args.command == "serve":
            serve(state, port=args.port)
        return 0
    except (Rejected, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
