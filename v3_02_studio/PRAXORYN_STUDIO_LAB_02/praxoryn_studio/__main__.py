"""CLI for the approval-gated studio lab. All paths must remain private."""
import argparse
import json
import sys
from pathlib import Path
from .engine import (initialize, submit, run_one, list_jobs,
                     get_job, approve, export, doctor, JobError)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='praxoryn_studio')
    parser.add_argument('--home', type=Path, default=Path('studio-private'))
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init')
    add=sub.add_parser('submit')
    add.add_argument('--tenant', required=True)
    add.add_argument('--kind', required=True)
    add.add_argument('--prompt-file', type=Path, required=True)
    sub.add_parser('work-once')
    ls=sub.add_parser('list');ls.add_argument('--tenant',required=True)
    one=sub.add_parser('show');one.add_argument('--tenant',required=True);one.add_argument('job_id')
    ap=sub.add_parser('approve');ap.add_argument('--tenant',required=True)
    ap.add_argument('--reviewer',required=True);ap.add_argument('job_id')
    exp=sub.add_parser('export');exp.add_argument('--tenant',required=True);exp.add_argument('job_id')
    sub.add_parser('doctor')
    server=sub.add_parser('serve-readonly');server.add_argument('--port',type=int,default=8769)
    args=parser.parse_args(argv)
    home=args.home
    try:
        if args.cmd == 'init':out={'database':str(initialize(home))}
        elif args.cmd == 'submit':
            out={'job_id':submit(home,args.tenant,args.kind,args.prompt_file.read_text(encoding='utf-8'))}
        elif args.cmd == 'work-once':out={'processed':run_one(home)}
        elif args.cmd == 'list':out={'jobs':list_jobs(home,args.tenant)}
        elif args.cmd == 'show':out=get_job(home,args.tenant,args.job_id)
        elif args.cmd == 'approve':
            approve(home,args.tenant,args.job_id,args.reviewer);out={'status':'approved'}
        elif args.cmd == 'export':out={'archive':str(export(home,args.tenant,args.job_id))}
        elif args.cmd == 'doctor':out=doctor(home)
        elif args.cmd == 'serve-readonly':
            from .read_only import serve
            serve(home,args.port);return 0
        print(json.dumps(out,indent=2,ensure_ascii=False))
        return 0
    except (OSError,ValueError,JobError) as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
