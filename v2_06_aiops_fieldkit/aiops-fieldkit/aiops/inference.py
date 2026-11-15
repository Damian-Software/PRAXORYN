"""Minimal client for an existing OpenAI-compatible local model API."""
from __future__ import annotations
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 2_000_000


def local_chat(prompt: str, *, timeout: float = 45.0) -> str:
    endpoint = os.environ.get("AI_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    url = urlparse(endpoint)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query:
        raise ValueError("This laboratory permits loopback HTTP endpoints only")
    model = os.environ.get("AI_MODEL", "")
    if not model or len(model) > 128:
        raise ValueError("Set AI_MODEL to the model ID returned by /v1/models")
    if not isinstance(prompt, str) or not (1 <= len(prompt) <= 16000):
        raise ValueError("Prompt length out of range")
    payload = {"model": model, "stream": False, "max_tokens": 384,
               "messages": [{"role": "system", "content": "Produce a draft only. Never claim to have taken actions."},
                            {"role": "user", "content": prompt}]}
    headers = {"Content-Type": "application/json"}
    secret = os.environ.get("AI_API_KEY", "")
    if secret:
        headers["Authorization"] = "Bearer " + secret
    request = Request(endpoint + "/v1/chat/completions", data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        blob = response.read(MAX_RESPONSE_BYTES + 1)
        if len(blob) > MAX_RESPONSE_BYTES:
            raise ValueError("Model response too large")
        parsed = json.loads(blob)
    content = parsed["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("Unsupported response structure")
    return content
