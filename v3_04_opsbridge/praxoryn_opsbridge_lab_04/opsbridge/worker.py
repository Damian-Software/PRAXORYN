"""Render reviewed artifacts; never execute model-generated shell commands."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path
from .core import claim_job, complete_job, path_under
from .adapters import generate_text, comfy_submit, comfy_history, comfy_view


def safe_write(target, content):
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(content)
    return target


def render_offline(job, dest):
    payload = json.loads(job['payload_json'])
    if job['kind'] == 'summary':
        source = str(payload.get('text',''))[:8000]
        # This is a deterministic demonstration, not AI-generated summary.
        lines = [x.strip() for x in source.split('.') if x.strip()]
        text = 'OFFLINE FIXTURE — NOT AI OUTPUT\n\n'+'\n'.join(f'- {x}.' for x in lines[:8])
        return safe_write(dest/'summary.txt',text.encode('utf-8'))
    if job['kind'] == 'code_review':
        text = str(payload.get('source',''))[:8000]
        issues = []
        if 'eval(' in text:
            issues.append({'code':'DEMO_EVAL','severity':'review','line':None})
        if 'shell=True' in text:
            issues.append({'code':'DEMO_SHELL','severity':'review','line':None})
        report = {'mode':'offline_fixture','findings':issues,
                  'warning':'Keyword exercise only; use Ruff/clang-tidy for real analysis'}
        return safe_write(dest/'findings.json',json.dumps(report,indent=2).encode())
    if job['kind'] == 'document':
        title = str(payload.get('title','Untitled'))[:100]
        content = str(payload.get('body',''))[:10000]
        markup = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Export</title>'
        import html
        markup += '<h1>'+html.escape(title)+'</h1><pre>'+html.escape(content)+'</pre></html>'
        return safe_write(dest/'draft.html',markup.encode('utf-8'))
    if job['kind'] == 'image':
        # Image generation requires a human-exported ComfyUI API workflow.
        return safe_write(dest/'README.txt',b'Image job requires an approved ComfyUI workflow.\n')
    raise ValueError('unknown job kind')


def run_one(db, root, backend='offline', base='http://127.0.0.1:8080/v1', model='local'):
    job = claim_job(db)
    if not job:
        return None
    job_id = job['job_id']
    dest = path_under(root,'private-artifacts',job['tenant'],job_id)
    try:
        if backend == 'offline':
            output = render_offline(job,dest)
        elif backend == 'llm' and job['kind']=='summary':
            data = json.loads(job['payload_json'])
            result = generate_text(base,model,str(data.get('text',''))[:8000])
            output = safe_write(dest/'model-draft.txt',result.encode('utf-8'))
        else:
            raise ValueError('backend does not support this job kind')
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        safe_write(dest/'manifest.json',json.dumps({'job_id':job_id,'artifact':output.name,
                   'sha256':digest},indent=2).encode('utf-8'))
        complete_job(db,job_id,output)
    except (ValueError, OSError, KeyError, RuntimeError, TimeoutError) as exc:
        # Only an error category enters audit, not the exception text.
        complete_job(db,job_id,error_code=type(exc).__name__)
    return job_id
