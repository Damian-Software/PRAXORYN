"""Small read-only/local-model client for existing API servers.

This is a training client, not an authentication gateway. It intentionally
allows loopback HTTP addresses only, and never logs prompts or credentials.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ApiClientError(Exception):
    """A sanitized error suitable for a local diagnostics tool."""


@dataclass(frozen=True)
class ApiProfile:
    family: str
    base_url: str
    model: str
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.family not in {"openai", "ollama"}:
            raise ValueError("Unsupported API family")
        if not 0.1 <= self.timeout <= 300:
            raise ValueError("Timeout must be between 0.1 and 300 seconds")
        if not self.model.strip():
            raise ValueError("Model identifier must not be empty")
        url = urlsplit(self.base_url)
        if (url.scheme != "http" or url.hostname not in
                {"127.0.0.1", "localhost", "::1"} or url.username or
                url.password or url.query or url.fragment):
            raise ValueError("Only loopback HTTP API addresses are allowed")
        expected = "/v1" if self.family == "openai" else "/api"
        if url.path.rstrip("/") != expected:
            raise ValueError(f"Expected API path: {expected}")
        if url.port is not None and not (1 <= url.port <= 65535):
            raise ValueError("Invalid port")


def request_json(profile: ApiProfile, method: str, route: str,
                 payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if route not in {"models", "chat/completions", "tags", "chat"}:
        raise ValueError("Unexpected API route")
    if method not in {"GET", "POST"}:
        raise ValueError("Unexpected method")
    url = profile.base_url.rstrip("/") + "/" + route
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=profile.timeout) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
    except HTTPError as exc:
        raise ApiClientError(f"Upstream returned HTTP {exc.code}") from None
    except (URLError, OSError, TimeoutError):
        raise ApiClientError("Local upstream is unreachable or timed out") from None
    if status != 200:
        raise ApiClientError(f"Unexpected HTTP status: {status}")
    if len(data) > MAX_RESPONSE_BYTES:
        raise ApiClientError("Response exceeded the configured size limit")
    try:
        result = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        raise ApiClientError("Upstream returned invalid JSON") from None
    if not isinstance(result, dict):
        raise ApiClientError("Upstream returned an unexpected JSON type")
    return result


def list_models(profile: ApiProfile) -> list[str]:
    if profile.family == "openai":
        response = request_json(profile, "GET", "models")
        records = response.get("data")
        key = "id"
    else:
        response = request_json(profile, "GET", "tags")
        records = response.get("models")
        key = "name"
    if not isinstance(records, list):
        raise ApiClientError("Model catalogue has an invalid shape")
    models: list[str] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get(key), str):
            raise ApiClientError("Model entry has an invalid shape")
        models.append(record[key])
    return models


def chat(profile: ApiProfile, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    payload = {"model": profile.model, "messages": messages, "stream": False}
    route = "chat/completions" if profile.family == "openai" else "chat"
    result = request_json(profile, "POST", route, payload)
    try:
        if profile.family == "openai":
            answer = result["choices"][0]["message"]["content"]
        else:
            answer = result["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ApiClientError("Chat response does not match the expected schema") from None
    if not isinstance(answer, str):
        raise ApiClientError("Chat content is not a string")
    return answer


def main() -> int:
    parser = argparse.ArgumentParser(description="Check an existing local AI API")
    parser.add_argument("--family", choices=["openai", "ollama"], required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", default="unused-for-listing")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--action", choices=["models", "chat"], default="models")
    parser.add_argument("--prompt", default="Reply with one short sentence.")
    args = parser.parse_args()
    try:
        profile = ApiProfile(args.family, args.base_url, args.model, args.timeout)
        if args.action == "models":
            print(json.dumps({"models": list_models(profile)}, ensure_ascii=False))
        else:
            print(chat(profile, args.prompt))
        return 0
    except (ApiClientError, ValueError) as exc:
        print(f"API check failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
