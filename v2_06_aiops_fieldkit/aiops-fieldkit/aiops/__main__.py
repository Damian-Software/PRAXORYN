"""Command line interface. Database path must stay in a private directory."""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import sys
import uuid
from .core import read_workspace_file, safe_write
from .finance import check_invoice_csv
from .codecheck import scan_python_file
from .guard import propose_from_jsonl
from .inference import local_chat
from . import store
from .report import write_html


def run(argv=None):
    parser=argparse.ArgumentParser(prog='python -m aiops')
    parser.add_argument('--db',default=os.environ.get('AIOPS_DB','./private/aiops.sqlite'))
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('init')
    t=sub.add_parser('tenant');t.add_argument('name');t.add_argument('--credit',type=int,default=10)
    s=sub.add_parser('submit');s.add_argument('tenant');s.add_argument('kind',choices=['summary','reply']);s.add_argument('file');s.add_argument('--workspace',default='./examples');s.add_argument('--key',default=None)
    w=sub.add_parser('work');w.add_argument('--mock',action='store_true')
    j=sub.add_parser('job');j.add_argument('tenant');j.add_argument('id',type=int)
    r=sub.add_parser('review');r.add_argument('tenant');r.add_argument('id',type=int);r.add_argument('decision',choices=['approve','reject']);r.add_argument('--actor',required=True)
    e=sub.add_parser('export');e.add_argument('tenant');e.add_argument('path')
    f=sub.add_parser('finance');f.add_argument('path')
    c=sub.add_parser('codecheck');c.add_argument('path')
    g=sub.add_parser('guard');g.add_argument('path');g.add_argument('--threshold',type=int,default=6)
    args=parser.parse_args(argv)
    if args.action in ('finance','codecheck','guard'):
        if args.action=='finance':output=check_invoice_csv(args.path)
        elif args.action=='codecheck':output=scan_python_file(args.path)
        else:output=propose_from_jsonl(args.path,args.threshold)
        print(json.dumps(output,indent=2,ensure_ascii=False));return 0
    private=pathlib.Path(args.db)
    if args.action=='init':
        private.parent.mkdir(parents=True,exist_ok=True)
        try:private.parent.chmod(0o700)
        except PermissionError:pass
        with store.connect(str(private)) as db:store.init(db)
        try:private.chmod(0o600)
        except PermissionError:pass
        print('Database initialized');return 0
    if not private.exists():raise ValueError('Run init first')
    with store.connect(str(private)) as db:
        if args.action=='tenant':
            store.create_tenant(db,args.name,args.credit);print('Tenant created');return 0
        if args.action=='submit':
            data,digest=read_workspace_file(args.workspace,args.file)
            text=data.decode('utf-8-sig')
            key=args.key or str(uuid.uuid4())
            id_=store.submit(db,args.tenant,args.kind,text,key)
            print(json.dumps({'job_id':id_,'sha256':digest,'key':key}));return 0
        if args.action=='work':
            job=store.lease_one(db)
            if not job:
                print('No queued jobs');return 0
            try:
                if args.mock:draft='MOCK DRAFT: '+job['input_text'][:120]
                else:draft=local_chat(('Summarize this for human review:\n' if job['kind']=='summary' else 'Draft a reply for human review:\n')+job['input_text'])
                store.complete(db,job['id'],draft)
                print(json.dumps({'job_id':job['id'],'state':'pending_review'}));return 0
            except Exception as exc:
                store.complete(db,job['id'],'',False)
                print('Worker failed; unit refunded. '+type(exc).__name__,file=sys.stderr);return 2
        if args.action=='job':
            job=store.get_job(db,args.tenant,args.id)
            if job is None:raise ValueError('Job not found in tenant')
            print(json.dumps(job,indent=2,ensure_ascii=False));return 0
        if args.action=='review':
            store.decide(db,args.tenant,args.id,args.actor,args.decision=='approve')
            print('Review recorded');return 0
        if args.action=='export':
            rows=[dict(x) for x in db.execute("SELECT id,kind,state,draft FROM jobs WHERE tenant_id=? AND state='approved' ORDER BY id",(args.tenant,))]
            write_html(args.path,'Approved drafts',rows)
            print('Offline HTML report created');return 0
    return 1


if __name__=='__main__':
    try:raise SystemExit(run())
    except (ValueError, OSError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(1)
