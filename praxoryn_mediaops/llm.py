"""Small client for existing OpenAI-compatible chat-completion endpoints."""
from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def chat(prompt: str, *, base_url: str, model: str, timeout: int = 120) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('The lab accepts only a local HTTP model endpoint')
    if not model or len(model) > 128:
        raise ValueError('invalid model identifier')
    url = base_url.rstrip('/') + '/v1/chat/completions'
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "stream": False, "max_tokens": 500, "temperature": 0.2}
    headers = {"Content-Type": "application/json"}
    token = os.environ.get('PRAXORYN_MODEL_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    payload = json.dumps(body).encode('utf-8')
    with urlopen(Request(url, data=payload, headers=headers, method='POST'), timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f'Unexpected HTTP status {response.status}')
        raw = response.read(2_000_000)
    result = json.loads(raw)
    text = result['choices'][0]['message']['content']
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError('empty model response')
    return text.strip()
