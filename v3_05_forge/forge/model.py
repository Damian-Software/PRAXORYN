"""Optional client for an existing, loopback-bound chat completions API."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError('Redirects are disabled for model calls')


def validate_base_url(url:str) -> str:
    parsed=urlsplit(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1','::1'):
        raise ValueError('Lab model endpoint must use http on numeric loopback')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Credentials, query and fragment forbidden in base URL')
    if not parsed.port or not 1024 <= parsed.port <= 65535:
        raise ValueError('Explicit unprivileged port required')
    if parsed.path not in ('','/','/v1','/v1/'):
        raise ValueError('Base URL must end in /v1')
    return f'http://127.0.0.1:{parsed.port}/v1'


def generate_text(prompt: str, backend: str='offline') -> tuple[str,str]:
    if backend == 'offline':
        # Explicitly synthetic: this is a pipeline check, not AI generation.
        return ('[OFFLINE DEMO] Draft for review. No inference was performed.','offline')
    if backend != 'local':
        raise ValueError('Backend must be offline or local')
    base=validate_base_url(os.environ.get('FORGE_MODEL_URL','http://127.0.0.1:8080/v1'))
    model=os.environ.get('FORGE_MODEL_ID','local-model')
    token=os.environ.get('FORGE_MODEL_TOKEN','')
    if len(prompt) > 8000:
        raise ValueError('Prompt over laboratory limit')
    data=json.dumps({'model':model,'messages':[{'role':'system','content':'Write concise draft text. No external actions.'},
                                                 {'role':'user','content':prompt}],
                     'stream':False,'max_tokens':384,'temperature':0.2}).encode()
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+'/chat/completions',data=data,headers=headers,method='POST')
    opener=urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=25) as resp:
            raw=resp.read(1_000_001)
            if len(raw)>1_000_000:raise ValueError('Model response too large')
    except (urllib.error.URLError,TimeoutError) as exc:
        raise RuntimeError('Local model API unavailable') from exc
    answer=json.loads(raw)['choices'][0]['message']['content']
    if not isinstance(answer,str):raise ValueError('Unexpected model response')
    return (answer[:12000],'local')
