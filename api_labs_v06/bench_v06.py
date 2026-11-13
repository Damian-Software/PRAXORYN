#!/usr/bin/env python3
"""Metadata-only benchmark for an existing OpenAI-compatible local chat API.

No prompt or response bodies are persisted. This is NOT a load generator.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time
from urllib import error, parse, request
from uuid import uuid4

SYNTHETIC_PROMPT = 'Respond with the exact word READY.'
MAX_RESPONSE_BYTES = 1024 * 1024


def endpoint(base_url: str, allow_remote: bool = False) -> str:
    parsed = parse.urlsplit(base_url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('A valid http(s) base URL is required')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Credentials, queries, and fragments are not allowed in the URL')
    local = parsed.hostname.lower() in ('localhost', '127.0.0.1', '::1')
    if not local and not allow_remote:
        raise ValueError('Remote endpoints require --allow-remote')
    if not local and parsed.scheme != 'https':
        raise ValueError('Remote endpoints require HTTPS')
    root = parsed.path.rstrip('/')
    if root not in ('', '/v1'):
        raise ValueError('Only the base endpoint or /v1 is supported')
    path = root if root else '/v1'
    return parse.urlunsplit((parsed.scheme, parsed.netloc, path + '/chat/completions', '', ''))


def _valid_count(value):
    return value if type(value) is int and value >= 0 else None


def measure(url: str, model: str, timeout_s: float = 60.0, max_tokens: int = 32, opener=None):
    """Return a metrics record; never include response or prompt content."""
    body = json.dumps({
        'model': model,
        'stream': False,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': SYNTHETIC_PROMPT}],
    }).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    key = os.getenv('LOCALAI_API_KEY')
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = request.Request(url, data=body, headers=headers, method='POST')
    opener = opener or request.urlopen
    start = time.perf_counter()
    result = {'ok': False, 'status_code': None, 'latency_ms': None,
              'completion_tokens': None, 'prompt_tokens': None,
              'tokens_per_second_e2e': None, 'error_class': None}
    try:
        with opener(req, timeout=timeout_s) as response:
            result['status_code'] = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError('Response limit exceeded')
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get('choices'), list) or not data['choices']:
            raise ValueError('Unexpected chat completion response')
        usage = data.get('usage') or {}
        if not isinstance(usage, dict):
            usage = {}
        result['completion_tokens'] = _valid_count(usage.get('completion_tokens'))
        result['prompt_tokens'] = _valid_count(usage.get('prompt_tokens'))
        result['ok'] = True
    except error.HTTPError as exc:
        result['status_code'] = exc.code
        result['error_class'] = 'HTTPError'
    except (error.URLError, TimeoutError, OSError) as exc:
        result['error_class'] = type(exc).__name__
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        result['error_class'] = type(exc).__name__
    finally:
        duration = time.perf_counter() - start
        result['latency_ms'] = round(duration * 1000, 3)
        tokens = result['completion_tokens']
        if result['ok'] and tokens is not None and duration > 0:
            result['tokens_per_second_e2e'] = round(tokens / duration, 4)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8080/v1')
    parser.add_argument('--allow-remote', action='store_true')
    parser.add_argument('--model', required=True)
    parser.add_argument('--warmup', type=int, default=2)
    parser.add_argument('--repetitions', type=int, default=10)
    parser.add_argument('--max-tokens', type=int, default=32)
    parser.add_argument('--timeout', type=float, default=60.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 0 <= args.warmup <= 100 or not 1 <= args.repetitions <= 1000:
        parser.error('Invalid warmup/repetition count')
    if not 1 <= args.max_tokens <= 4096 or not 0 < args.timeout <= 600:
        parser.error('Invalid max token count or timeout')
    url = endpoint(args.base_url, args.allow_remote)
    run_id = str(uuid4())
    for _ in range(args.warmup):
        measure(url, args.model, args.timeout, args.max_tokens)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', encoding='utf-8') as stream:
        for index in range(args.repetitions):
            row = measure(url, args.model, args.timeout, args.max_tokens)
            row.update({'run_id': run_id, 'index': index + 1, 'model': args.model, 'phase': 'warm'})
            stream.write(json.dumps(row, separators=(',', ':')) + '\n')
            stream.flush()
            print(f"{index + 1}/{args.repetitions}: {'ok' if row['ok'] else 'failed'} "
                  f"({row['latency_ms']} ms)")
    print('Saved metadata only:', args.output)


if __name__ == '__main__':
    main()
