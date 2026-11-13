#!/usr/bin/env python3
"""ComfyUI API-format job bridge: explicit workflow, no invented image generation."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8188"
MAX_WORKFLOW = 512_000

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("ComfyUI redirect refused")

OPENER = urllib.request.build_opener(NoRedirect)


def read_workflow(path: pathlib.Path) -> dict:
    data = path.read_bytes()
    if len(data) > MAX_WORKFLOW:
        raise ValueError("Workflow file is too large")
    obj = json.loads(data)
    if not isinstance(obj, dict) or not obj:
        raise ValueError("A non-empty API-format JSON object is required")
    for identifier, node in obj.items():
        if not isinstance(node, dict) or "class_type" not in node or "inputs" not in node:
            raise ValueError("Workflow must use ComfyUI API format, not UI canvas format")
    return obj


def request_json(path: str, *, payload: dict | None = None) -> dict:
    if not path.startswith("/"):
        raise ValueError("Invalid local route")
    raw = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if raw is not None else {}
    req = urllib.request.Request(BASE + path, data=raw, headers=headers)
    with OPENER.open(req, timeout=20) as response:
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("Unexpectedly large JSON response")
    result = json.loads(data)
    if not isinstance(result, dict):
        raise ValueError("Expected JSON object")
    return result


def submit(workflow: dict) -> str:
    result = request_json("/prompt", payload={"prompt": workflow, "client_id": "praxoryn-local-example"})
    identifier = result.get("prompt_id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-fA-F-]{32,36}", identifier):
        raise RuntimeError("ComfyUI did not return a valid prompt_id; inspect node_errors")
    return identifier


def history(identifier: str) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F-]{32,36}", identifier):
        raise ValueError("Invalid prompt_id")
    return request_json("/history/" + identifier)


def fetch_image(filename: str, subfolder: str, folder_type: str, target: pathlib.Path) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", filename) or filename in {".", ".."}:
        raise ValueError("Unsafe filename")
    if not re.fullmatch(r"[A-Za-z0-9_-]{0,64}", subfolder):
        raise ValueError("Nested subdirectories are disabled in this example")
    if folder_type not in {"output", "temp"}:
        raise ValueError("Unsupported file type")
    query = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
    req = urllib.request.Request(BASE + "/view?" + query)
    with OPENER.open(req, timeout=30) as response:
        blob = response.read(15_000_001)
    if len(blob) > 15_000_000:
        raise ValueError("Image exceeds configured size limit")
    # Trust the file signature, not a remote filename extension.
    if not (blob.startswith(b"\x89PNG\r\n\x1a\n") or blob.startswith(b"\xff\xd8\xff") or (blob.startswith(b"RIFF") and blob[8:12] == b"WEBP")):
        raise ValueError("Unexpected image file signature")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(blob)
    return {"path": str(target), "size": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    dry = sub.add_parser("validate"); dry.add_argument("workflow")
    send = sub.add_parser("queue"); send.add_argument("workflow")
    check = sub.add_parser("history"); check.add_argument("prompt_id")
    grab = sub.add_parser("fetch")
    for name in ("filename", "subfolder", "type", "target"):
        grab.add_argument(name)
    args = p.parse_args()
    if args.cmd == "validate":
        workflow = read_workflow(pathlib.Path(args.workflow))
        print(json.dumps({"valid_shape": True, "nodes": len(workflow), "model_execution": False}))
    elif args.cmd == "queue":
        print(json.dumps({"prompt_id": submit(read_workflow(pathlib.Path(args.workflow)))}))
    elif args.cmd == "history":
        print(json.dumps(history(args.prompt_id)))
    else:
        print(json.dumps(fetch_image(args.filename, args.subfolder, args.type, pathlib.Path(args.target))))

if __name__ == "__main__":
    main()
