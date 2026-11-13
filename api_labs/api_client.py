"""LAB: simple client for EXISTING local APIs, no custom HTTP server.

Only loopback preset addresses are used. No credential or prompt is logged.
Network calls require an already-running local llama.cpp or Ollama server.
"""
from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

BASE_URLS = {
    "llama": "http://127.0.0.1:8081",
    "ollama": "http://127.0.0.1:11434",
}
MAX_REPLY_BYTES = 2_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Refusing redirect from local backend")


class APIError(Exception):
    pass


def request_json(provider: str, path: str, data: dict | None = None, *, timeout: int = 15) -> dict:
    if provider not in BASE_URLS:
        raise ValueError("Unknown provider; only local allowlisted providers are permitted")
    if not path.startswith("/") or path.startswith("//") or ".." in path or "?" in path:
        raise ValueError("Invalid API route")
    raw = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    if raw is not None and len(raw) > 32_768:
        raise ValueError("Request exceeds lab limit")
    req = Request(
        BASE_URLS[provider] + path,
        data=raw,
        method="POST" if raw is not None else "GET",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            body = response.read(MAX_REPLY_BYTES + 1)
            if len(body) > MAX_REPLY_BYTES:
                raise APIError("Response body too large")
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise APIError("JSON response is not an object")
            return payload
    except HTTPError as exc:
        # Do not echo remote response body: it could include prompts or secrets.
        raise APIError(f"Upstream returned HTTP {exc.code}") from None
    except (URLError, TimeoutError) as exc:
        raise APIError(f"Local backend is unreachable or timed out ({type(exc).__name__})") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise APIError(f"Invalid upstream JSON ({type(exc).__name__})") from None


def model_ids(provider: str) -> list[str]:
    if provider == "llama":
        items = request_json(provider, "/v1/models").get("data", [])
        return [x["id"] for x in items if isinstance(x, dict) and isinstance(x.get("id"), str)]
    if provider == "ollama":
        items = request_json(provider, "/api/tags").get("models", [])
        return [x["name"] for x in items if isinstance(x, dict) and isinstance(x.get("name"), str)]
    raise ValueError("Unsupported provider")


def chat(provider: str, model: str, prompt: str) -> str:
    if not model or len(model) > 200 or len(prompt.encode("utf-8")) > 8192:
        raise ValueError("Invalid model/prompt size")
    messages = [{"role": "user", "content": prompt}]
    if provider == "llama":
        payload = request_json(provider, "/v1/chat/completions", {
            "model": model, "messages": messages, "max_tokens": 128, "stream": False,
        }, timeout=120)
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise APIError("Unexpected Chat Completions response") from None
    if provider == "ollama":
        payload = request_json(provider, "/api/chat", {
            "model": model, "messages": messages,
            "options": {"num_predict": 128}, "stream": False,
        }, timeout=120)
        try:
            return payload["message"]["content"]
        except (KeyError, TypeError):
            raise APIError("Unexpected Ollama chat response") from None
    raise ValueError("Unsupported provider")


def main():
    parser = argparse.ArgumentParser(description="Client for existing local inference APIs")
    parser.add_argument("provider", choices=tuple(BASE_URLS))
    parser.add_argument("operation", choices=("models", "chat"))
    parser.add_argument("--model", default="")
    parser.add_argument("--prompt", default="")
    args = parser.parse_args()
    try:
        if args.operation == "models":
            for model in model_ids(args.provider):
                print(model)
        else:
            if not args.model or not args.prompt:
                parser.error("chat needs --model and --prompt")
            print(chat(args.provider, args.model, args.prompt))
    except (APIError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
