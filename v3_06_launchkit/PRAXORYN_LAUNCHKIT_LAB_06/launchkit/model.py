"""Calls an existing OpenAI-compatible chat completion endpoint, never invents one."""
from __future__ import annotations
import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from .security import Rejected

class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise Rejected("Redirect from model endpoint refused")


def model_response(prompt: str, *, endpoint: str, model: str, api_key: str = "") -> str:
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname is None or parsed.username or parsed.password:
        raise Rejected("Use an HTTP endpoint on numeric loopback")
    try:
        if not ipaddress.ip_address(parsed.hostname).is_loopback:
            raise Rejected("Non-loopback addresses need a separate network security design")
    except ValueError as exc:
        raise Rejected("Use numeric 127.0.0.1 or ::1") from exc
    if parsed.path.rstrip("/") != "/v1/chat/completions" or parsed.query or parsed.fragment:
        raise Rejected("Endpoint must end in /v1/chat/completions")
    if len(prompt.encode("utf-8")) > 12_000:
        raise Rejected("Prompt exceeds the lab input limit")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": "Summarize the supplied synthetic business note. Return a draft only."},
                     {"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 480,
        "temperature": 0.1,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
    opener = urllib.request.build_opener(RefuseRedirect)
    with opener.open(request, timeout=25) as response:
        raw = response.read(512_001)
    if len(raw) > 512_000:
        raise Rejected("Model response exceeds size limit")
    parsed_response = json.loads(raw)
    text = parsed_response["choices"][0]["message"]["content"]
    if not isinstance(text, str):
        raise Rejected("Unexpected model response schema")
    return text[:16_000]
