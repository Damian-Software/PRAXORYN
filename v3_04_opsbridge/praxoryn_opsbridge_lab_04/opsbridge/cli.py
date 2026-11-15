"""A small reproducible CLI for Debian/WSL2 training labs."""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from .core import open_db, create_job, list_jobs, transition, verify_audit
from .worker import run_one
from .adapters import comfy_submit, comfy_history


def parser():
    p=argparse.ArgumentParser(prog='opsbridge')
    p.add_argument('--root', default=os.environ.get('OPSBRIDGE_HOME', str(Path.home()/'opsbridge-data')))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    c=sub.add_parser('create');c.add_argument('--tenant',required=True);c.add_argument('--kind',required=True)
    c.add_argument('--input',required=True,help='JSON input file; do not pass customer data as shell argument')
    w=sub.add_parser('worker-once');w.add_argument('--backend',choices=['offline','llm'],default='offline')
    w.add_argument('--base',default='http://127.0.0.1:8080/v1');w.add_argument('--model',default='local')
    l=sub.add_parser('list');l.add_argument('--tenant',required=True)
    a=sub.add_parser('approve');a.add_argument('--job-id',required=True);a.add_argument('--actor',required=True)
    r=sub.add_parser('release');r.add_argument('--job-id',required=True);r.add_argument('--actor',required=True)
    x=sub.add_parser('reject');x.add_argument('--job-id',required=True);x.add_argument('--actor',required=True)
    sub.add_parser('verify-audit')
    cc=sub.add_parser('comfy-submit');cc.add_argument('--base',default='http://127.0.0.1:8188')
    cc.add_argument('--workflow',required=True)
    hh=sub.add_parser('comfy-history');hh.add_argument('--base',default='http://127.0.0.1:8188')
    hh.add_argument('--prompt-id',required=True)
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    db=open_db(args.root)
    if args.command=='init':
        print('ready:', Path(args.root).resolve())
    elif args.command=='create':
        payload=json.loads(Path(args.input).read_text(encoding='utf-8'))
        print(create_job(db,args.tenant,args.kind,payload))
    elif args.command=='worker-once':
        print(run_one(db,args.root,args.backend,args.base,args.model) or 'queue_empty')
    elif args.command=='list':
        print(json.dumps(list_jobs(db,args.tenant),indent=2))
    elif args.command in ('approve','release','reject'):
        target={'approve':('review','approved'),
                'release':('approved','released'),
                'reject':('review','rejected')}[args.command]
        transition(db,args.job_id,*target,args.actor)
        print(target[1])
    elif args.command=='verify-audit':
        ok,bad=verify_audit(db);print('ok' if ok else 'broken_at_event:'+str(bad))
        if not ok:return 2
    elif args.command=='comfy-submit':
        workflow=json.loads(Path(args.workflow).read_text(encoding='utf-8'))
        print(comfy_submit(args.base,workflow))
    elif args.command=='comfy-history':
        print(json.dumps(comfy_history(args.base,args.prompt_id),indent=2))
    return 0

if __name__=='__main__':sys.exit(main())
