"""Small client for existing OpenAI-compatible chat completion endpoints.

No external Python dependencies. Never prints secrets or full HTTP error bodies.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


class APIError(Exception):
    pass


def read_key(path: str) -> str:
    key_file = Path(path).expanduser()
    if not key_file.is_file():
        raise APIError(f"API key file not found: {key_file}")
    key = key_file.read_text(encoding="utf-8").strip()
    if not key or "\n" in key or "\r" in key:
        raise APIError("API key file must contain exactly one nonempty key")
    return key


class LocalChatClient:
    def __init__(self, base_url: str, key: str, timeout: float = 45.0) -> None:
        if not base_url.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
            raise APIError("Use loopback HTTP or an HTTPS endpoint")
        if not 0 < timeout <= 300:
            raise APIError("timeout must be in (0, 300]")
        self.base_url = base_url.rstrip("/")
        self.key = key
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}))

    def chat(self, prompt: str, model: str = "local-chat", max_tokens: int = 64) -> str:
        if not (1 <= len(prompt) <= 8000):
            raise APIError("Prompt length must be 1..8000 characters")
        if not model or len(model) > 128:
            raise APIError("Invalid model ID")
        if not (1 <= max_tokens <= 1024):
            raise APIError("max_tokens must be 1..1024")
        payload = json.dumps({"model": model,
                              "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0, "max_tokens": max_tokens,
                              "stream": False}).encode("utf-8")
        request = Request(self.base_url + "/v1/chat/completions", data=payload,
                          headers={"Content-Type": "application/json",
                                   "Authorization": f"Bearer {self.key}"}, method="POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) > 2_000_000:
                    raise APIError("Response too large")
                raw = response.read(2_000_001)
        except HTTPError as exc:
            raise APIError(f"Upstream returned HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError) as exc:
            raise APIError(f"Cannot reach upstream ({type(exc).__name__})") from None
        if len(raw) > 2_000_000:
            raise APIError("Response too large")
        try:
            data = json.loads(raw)
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str):
                raise ValueError("Content must be text")
            return text
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise APIError("Invalid chat response schema") from None


def main() -> int:
    parser = argparse.ArgumentParser(description="Existing chat API client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--key-file", default=os.path.expanduser("~/.config/localai/api_keys.txt"))
    parser.add_argument("--model", default="local-chat")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-tokens", type=int, default=64)
    args = parser.parse_args()
    try:
        client = LocalChatClient(args.base_url, read_key(args.key_file))
        print(client.chat(args.prompt, args.model, args.max_tokens))
    except APIError as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
