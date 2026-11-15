"""Praxoryn Forge - stdlib-first local workflow lab.

Usage: python -m forge --home ./state init|submit|run-once|show|review|audit|demo
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from .files import safe_output_dir,write_private,digest_file
from .plugins import execute,read_manifest
from .store import open_db,submit,claim,complete,review,get_job,events


def root_dir(home:str) -> Path:
    root=Path(home).expanduser().resolve()
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    for child in ('inputs','results'):
        p=root/child;p.mkdir(exist_ok=True,mode=0o700)
        os.chmod(p,0o700)
    return root


def run_once(con,home:Path,backend:str) -> dict:
    row=claim(con)
    if not row:return {'status':'empty'}
    try:
        payload=json.loads(row['input_json'])
        result=execute(home/'inputs',payload,row['kind'],backend)
        dest=safe_output_dir(home/'results',row['id'])
        output=dest/'result.json'
        write_private(output,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        output_sha=digest_file(output)
        complete(con,row['tenant'],row['id'],{'file':str(output),'sha256':output_sha},'waiting_review')
        return {'status':'waiting_review','id':row['id'],'sha256':output_sha}
    except Exception as exc:
        # Only a stable code is recorded, no prompt, file content, or stack trace.
        complete(con,row['tenant'],row['id'],{'reason_code':exc.__class__.__name__},'failed')
        return {'status':'failed','id':row['id'],'reason_code':exc.__class__.__name__}


def main(argv=None):
    p=argparse.ArgumentParser(description='Local, no-container enterprise workflow lab')
    p.add_argument('--home',default='./forge-state',help='Private data directory')
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('init')
    s=sub.add_parser('submit');s.add_argument('--tenant',required=True);s.add_argument('--plugin',required=True)
    s.add_argument('--payload',required=True,help='Path to JSON payload file')
    s.add_argument('--key',required=True,help='Idempotency key')
    s=sub.add_parser('run-once');s.add_argument('--backend',choices=['offline','local'],default='offline')
    s=sub.add_parser('show');s.add_argument('--tenant',required=True);s.add_argument('--id',required=True)
    s=sub.add_parser('review');s.add_argument('--tenant',required=True);s.add_argument('--id',required=True)
    s.add_argument('--decision',choices=['approved','rejected'],required=True)
    s.add_argument('--reviewer',required=True)
    s=sub.add_parser('audit');s.add_argument('--tenant',required=True)
    sub.add_parser('demo')
    args=p.parse_args(argv)
    home=root_dir(args.home)
    with open_db(home/'db.sqlite') as con:
        if args.action=='init':
            result={'status':'initialized','home':str(home)}
        elif args.action=='submit':
            manifest=read_manifest(Path(__file__).resolve().parent.parent/'plugins',args.plugin)
            payload=json.loads(Path(args.payload).read_text(encoding='utf-8'))
            result=submit(con,args.tenant,manifest['kind'],payload,args.key)
            result={k:result[k] for k in ('id','tenant','kind','state')}
        elif args.action=='run-once':result=run_once(con,home,args.backend)
        elif args.action=='show':
            j=get_job(con,args.tenant,args.id)
            result={'id':j['id'],'tenant':j['tenant'],'kind':j['kind'],'state':j['state'],
                    'result':json.loads(j['result_json']) if j['result_json'] else None}
        elif args.action=='review':
            review(con,args.tenant,args.id,args.decision,args.reviewer)
            result={'status':args.decision,'id':args.id}
        elif args.action=='audit':result=events(con,args.tenant)
        else:
            # No external API, no real customer data, no automatic approval.
            input_src=Path(__file__).resolve().parent.parent/'examples'/'invoice.csv'
            input_dest=home/'inputs'/'invoice.csv'
            if not input_dest.exists():input_dest.write_bytes(input_src.read_bytes())
            job=submit(con,'example','invoice',{'filename':'invoice.csv','expected_total':'45.50'},'demo-invoice-001')
            outcome=run_once(con,home,'offline') if job['state']=='queued' else {'status':'already_exists'}
            result={'job':job['id'],'run':outcome,'state':get_job(con,'example',job['id'])['state']}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':sys.exit(main())
