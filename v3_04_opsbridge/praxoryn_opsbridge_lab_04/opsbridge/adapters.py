"""Explicit adapters for existing model and image-service APIs."""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def local_base(url, expected_port=None):
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'http' or u.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('only loopback HTTP endpoints permitted in this lab')
    if u.username or u.password or u.fragment:
        raise ValueError('userinfo and fragment are prohibited')
    if expected_port and u.port != expected_port:
        raise ValueError('unexpected port')
    return url.rstrip('/')


def fetch_json(url, payload=None, timeout=30, max_bytes=3 * 1024 * 1024):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    # urllib HTTP redirects could leave loopback, therefore disable them explicitly.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            raise ValueError('HTTP redirects are not permitted for local API adapters')
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(req, timeout=timeout) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError('upstream rejected request')
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError('upstream response too large')
    return json.loads(body.decode('utf-8'))


def generate_text(base, model, prompt):
    base = local_base(base)
    if not base.endswith('/v1'):
        raise ValueError('OpenAI-compatible base must end in /v1')
    reply = fetch_json(base+'/chat/completions', {
        'model':model, 'messages':[{'role':'user','content':prompt}],
        'stream':False, 'temperature':0, 'max_tokens':512
    },timeout=75)
    return reply['choices'][0]['message']['content']


def comfy_submit(base, workflow):
    base = local_base(base)
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError('workflow must be exported in ComfyUI API format')
    reply = fetch_json(base+'/prompt', {'prompt':workflow},timeout=20)
    if 'prompt_id' not in reply:
        raise RuntimeError('ComfyUI did not accept the workflow')
    return reply['prompt_id']


def comfy_history(base, prompt_id):
    base = local_base(base)
    safe_id = urllib.parse.quote(prompt_id, safe='')
    return fetch_json(base+'/history/'+safe_id,timeout=20)


def comfy_view(base, filename, subfolder='', category='output', size_limit=20*1024*1024):
    base = local_base(base)
    if category not in ('output', 'temp'):
        raise ValueError('unexpected ComfyUI image type')
    query = urllib.parse.urlencode({'filename':filename,'subfolder':subfolder,'type':category})
    req = urllib.request.Request(base+'/view?'+query)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            raise ValueError('redirect prohibited')
    with urllib.request.build_opener(NoRedirect).open(req,timeout=45) as response:
        body = response.read(size_limit+1)
    if len(body)>size_limit:
        raise ValueError('image exceeds size limit')
    if not (body.startswith(b'\x89PNG\r\n\x1a\n') or body.startswith(b'\xff\xd8\xff')):
        raise ValueError('expected PNG or JPEG output')
    return body
