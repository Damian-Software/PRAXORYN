"""Minimal, conservative client for an existing OpenAI-compatible local API."""
from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def safe_base(url: str) -> str:
    p = urlparse(url)
    if p.scheme != "http" or p.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("This laboratory only accepts loopback HTTP endpoints")
    if p.username or p.password or p.query or p.fragment or p.path not in {"", "/"}:
        raise ValueError("Use an origin URL without credentials, query or path")
    return url.rstrip("/")


def send(base: str, path: str, payload: dict | None = None, timeout: float = 12.0) -> tuple[int, dict]:
    base = safe_base(base)
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    token = os.getenv("PRAXOPS_API_KEY", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data else "GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024)
            status = response.status
    except urllib.error.HTTPError as e:
        # Deliberately do not propagate upstream error bodies: they can contain user content.
        raise ApiError(e.code, f"Upstream HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ApiError(0, f"Transport failure: {type(e).__name__}") from None
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ApiError(status, "Upstream returned invalid JSON") from None
    if not isinstance(obj, dict):
        raise ApiError(status, "Unexpected top-level JSON structure")
    return int((time.perf_counter() - started) * 1000), obj


def health(base: str, timeout: float = 5.0) -> dict:
    elapsed, payload = send(base, "/health", timeout=timeout)
    return {"ok": payload.get("status") == "ok", "latency_ms": elapsed}


def models(base: str, timeout: float = 8.0) -> list[str]:
    _, payload = send(base, "/v1/models", timeout=timeout)
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ApiError(200, "Missing model list")
    return [str(it["id"]) for it in data if isinstance(it, dict) and isinstance(it.get("id"), str)]


def chat(base: str, model: str, text: str, timeout: float = 90.0) -> tuple[int, str]:
    if not 1 <= len(text) <= 1000:
        raise ValueError("Demo prompt must contain 1..1000 characters")
    request = {"model": model, "messages": [{"role": "user", "content": text}], "stream": False, "max_tokens": 96, "temperature": 0}
    elapsed, payload = send(base, "/v1/chat/completions", request, timeout)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ApiError(200, "Missing choices")
    first = choices[0]
    content = first.get("message", {}).get("content") if isinstance(first, dict) else None
    if not isinstance(content, str):
        raise ApiError(200, "Missing response content")
    return elapsed, content
