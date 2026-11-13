"""ComfyUI local API adapter for user-exported API-format workflows."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit
import json
import time
import uuid


def _local(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != 'http' or parts.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('ComfyUI adapter is loopback-only')
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('unexpected base URL components')
    return url.rstrip('/')


def _read_json(url: str, *, body: dict | None = None, timeout: int = 30) -> dict:
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read(4_000_000))


def prepare(workflow: dict, node: str, field: str, prompt: str) -> dict:
    if not isinstance(workflow, dict) or node not in workflow:
        raise ValueError('prompt node not found in exported API workflow')
    graph = deepcopy(workflow)
    inputs = graph[node].get('inputs')
    if not isinstance(inputs, dict) or field not in inputs or not isinstance(inputs[field], str):
        raise ValueError('prompt input is not an editable text field')
    inputs[field] = prompt
    return graph


def submit_and_collect(*, base_url: str, workflow: dict, node: str, field: str,
                       prompt: str, destination: Path, wait_seconds: int = 480) -> list[Path]:
    base = _local(base_url)
    graph = prepare(workflow, node, field, prompt)
    reply = _read_json(base + '/prompt', body={'prompt': graph, 'client_id': str(uuid.uuid4())})
    if reply.get('error') or 'prompt_id' not in reply:
        raise RuntimeError(f'Workflow rejected: {reply.get("error", "missing prompt_id")}')
    prompt_id = reply['prompt_id']
    if not isinstance(prompt_id, str):
        raise RuntimeError('invalid prompt id')
    deadline = time.monotonic() + wait_seconds
    entry = None
    while time.monotonic() < deadline:
        history = _read_json(base + '/history/' + prompt_id)
        entry = history.get(prompt_id)
        if entry:
            status = entry.get('status') or {}
            if status.get('status_str') == 'error':
                raise RuntimeError('ComfyUI workflow failed; inspect server logs')
            if status.get('completed') is True or entry.get('outputs'):
                break
        time.sleep(2)
    else:
        raise TimeoutError('ComfyUI did not complete within the configured time')
    destination.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for node_out in (entry.get('outputs') or {}).values():
        for category in ('images', 'gifs', 'videos'):
            for i, item in enumerate(node_out.get(category, [])):
                if not isinstance(item, dict):
                    continue
                filename = item.get('filename', '')
                if not isinstance(filename, str) or Path(filename).name != filename:
                    raise RuntimeError('unexpected result filename')
                if Path(filename).suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.gif','.mp4','.webm'}:
                    continue
                query = urlencode({'filename': filename, 'subfolder': item.get('subfolder',''),
                                   'type': item.get('type','output')})
                url = base + '/view?' + query
                req = Request(url)
                with urlopen(req, timeout=60) as resp:
                    data = resp.read(40 * 1024 * 1024 + 1)
                if len(data) > 40 * 1024 * 1024:
                    raise RuntimeError('asset exceeds maximum lab size')
                ext = Path(filename).suffix.lower()
                path = destination / f'comfy-{len(outputs)+1:02d}{ext}'
                path.write_bytes(data)
                outputs.append(path)
    if not outputs:
        raise RuntimeError('no supported saved media output; verify SaveImage/VideoCombine nodes')
    return outputs
