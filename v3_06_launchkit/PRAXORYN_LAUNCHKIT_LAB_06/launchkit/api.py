"""Loopback-only HTTP example. Add audited TLS ingress before external use."""
from __future__ import annotations
import json
import os
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from . import db
from .security import Rejected, safe_json

MAX_BODY = 64 * 1024

class RequestError(Exception):
    def __init__(self, status: int, reason: str):
        super().__init__(reason)
        self.status = status
        self.reason = reason


def create_handler(state: Path):
    class LocalHandler(BaseHTTPRequestHandler):
        server_version = "PraxorynLaunchKit/0.1"
        sys_version = ""
        protocol_version = "HTTP/1.0"

        def log_message(self, format_string, *args):
            # No raw URLs, authorization headers, request bodies or prompts in logs.
            return

        def json_reply(self, status: int, item: dict | list):
            content = (safe_json(item, limit=524_288) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def read_body(self) -> dict:
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise RequestError(415, "JSON content type required")
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                raise RequestError(400, "Invalid Content-Length")
            if length < 0 or length > MAX_BODY:
                raise RequestError(413, "Invalid or excessive request size")
            try:
                obj = json.loads(self.rfile.read(length))
            except (UnicodeError, json.JSONDecodeError):
                raise RequestError(400, "Malformed JSON")
            if not isinstance(obj, dict):
                raise RequestError(400, "JSON object expected")
            return obj

        def principal(self, conn):
            value = self.headers.get("Authorization", "")
            if not value.startswith("Bearer "):
                raise RequestError(401, "Bearer token required")
            principal = db.authenticate(conn, value.removeprefix("Bearer "))
            if not principal:
                raise RequestError(401, "Invalid token")
            return principal

        def require(self, actor, *roles):
            if actor["scope"] not in roles and actor["scope"] != "admin":
                raise RequestError(403, "Insufficient scope")

        def handle_api(self, method):
            route = urlsplit(self.path)
            parts = route.path.strip("/").split("/")
            if route.path == "/health" and method == "GET":
                self.json_reply(200, {"status": "ok", "storage": "sqlite", "model": "not_checked"})
                return
            if route.query:
                raise RequestError(400, "Query parameters not accepted")
            with closing(db.open_db(state)) as conn:
                actor = self.principal(conn)
                tenant = actor["tenant"]
                if route.path == "/v1/jobs" and method == "GET":
                    self.require(actor, "read", "submit", "approve")
                    self.json_reply(200, {"jobs": db.list_jobs(conn, tenant)})
                    return
                if route.path == "/v1/jobs" and method == "POST":
                    self.require(actor, "submit")
                    payload = self.read_body()
                    if not isinstance(payload.get("payload"), dict):
                        raise RequestError(400, "payload must be an object")
                    jid, created = db.submit(conn, tenant, payload.get("kind"),
                                             payload["payload"], payload.get("idempotency_key"))
                    self.json_reply(201 if created else 200, {"job_id": jid, "created": created})
                    return
                if len(parts) == 3 and parts[:2] == ["v1", "jobs"] and method == "GET":
                    self.require(actor, "read", "submit", "approve")
                    job = db.get_job(conn, tenant, parts[2])
                    if job is None:
                        raise RequestError(404, "Job not found")
                    self.json_reply(200, job)
                    return
                if len(parts) == 4 and parts[:2] == ["v1", "jobs"] and parts[3] == "approve" and method == "POST":
                    self.require(actor, "approve")
                    obj = self.read_body()
                    db.approve(conn, tenant, parts[2], obj.get("reviewer", ""))
                    self.json_reply(200, {"status": "approved"})
                    return
            raise RequestError(404, "Unknown route")

        def dispatch(self, method):
            try:
                self.handle_api(method)
            except RequestError as exc:
                self.json_reply(exc.status, {"error": exc.reason})
            except Rejected as exc:
                self.json_reply(422, {"error": str(exc)})
            except Exception:
                # Never reflect internal exceptions or secrets in public HTTP responses.
                self.json_reply(500, {"error": "Internal server error"})

        def do_GET(self):
            self.dispatch("GET")

        def do_POST(self):
            self.dispatch("POST")

    return LocalHandler


def serve(state: Path, bind: str = "127.0.0.1", port: int = 8787):
    if bind not in {"127.0.0.1", "::1"}:
        raise Rejected("Teaching server is restricted to numeric loopback")
    httpd = ThreadingHTTPServer((bind, port), create_handler(state))
    print(f"Listening on {bind}:{port} (loopback; TLS not enabled)")
    httpd.serve_forever()
