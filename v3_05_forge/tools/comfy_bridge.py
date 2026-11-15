"""Local ComfyUI API workflow launcher; never generates synthetic AI claims.

Requires a user-exported API-format workflow; no automatic node installation.
"""
from __future__ import annotations
import argparse
import json
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlsplit

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError('Redirect rejected')


def origin(value:str) -> str:
    u=urlsplit(value)
    if u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.path not in ('','/'):
        raise ValueError('ComfyUI must use numeric loopback address and explicit port')
    return f'http://127.0.0.1:{u.port}'


def load_api_workflow(path:Path) ->dict:
    if path.stat().st_size>1_000_000:raise ValueError('Workflow too large')
    graph=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(graph,dict) or not 1<=len(graph)<=500:
        raise ValueError('Expected nonempty API-format node map')
    for key,node in graph.items():
        if not isinstance(key,str) or not isinstance(node,dict) or not isinstance(node.get('class_type'),str):
            raise ValueError('This is not a valid API-format workflow; export using API format')
        if not isinstance(node.get('inputs',{}),dict):
            raise ValueError('Node inputs must be an object')
    return graph


def request_json(url:str, payload:dict|None=None)->dict:
    body=json.dumps(payload).encode() if payload is not None else None
    method='POST' if payload is not None else 'GET'
    req=urllib.request.Request(url,data=body,method=method,
       headers={'Content-Type':'application/json'} if body is not None else {})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
        result=response.read(2_000_001)
    if len(result)>2_000_000:raise ValueError('Response over limit')
    item=json.loads(result)
    if not isinstance(item,dict):raise ValueError('Invalid API response')
    return item


def submit(base:str,workflow:dict) ->str:
    address=origin(base)
    result=request_json(address+'/prompt',{'prompt':workflow,'client_id':str(uuid.uuid4())})
    prompt_id=result.get('prompt_id')
    if not isinstance(prompt_id,str) or not prompt_id:raise ValueError('ComfyUI rejected workflow or omitted prompt_id')
    return prompt_id


def status(base:str,prompt_id:str)->dict:
    uuid.UUID(prompt_id)
    history=request_json(origin(base)+'/history/'+prompt_id)
    return {'state':'finished' if prompt_id in history else 'pending',
            'prompt_id':prompt_id,'history':history.get(prompt_id,{})}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',default='http://127.0.0.1:8188')
    p.add_argument('--workflow',type=Path,required=True)
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--poll',action='store_true')
    args=p.parse_args()
    graph=load_api_workflow(args.workflow)
    if args.dry_run:
        print(json.dumps({'valid_api_nodes':len(graph),'remote_job_submitted':False}))
        return
    job=submit(args.url,graph)
    print(json.dumps({'prompt_id':job,'state':'submitted'}))
    if args.poll:
        for _ in range(24):
            answer=status(args.url,job)
            if answer['state']=='finished':
                # Report completion state but keep raw history local, never execute output paths.
                print(json.dumps({'prompt_id':job,'state':'finished'}))
                return
            time.sleep(5)
        raise SystemExit('Workflow is still running or could not be confirmed; inspect ComfyUI queue')

if __name__=='__main__':main()
