"""Local-first command interface."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .pipeline import publish
from .audit import show_events
from .plugins import run_tool
from .llm import chat


def main(argv=None):
    parser=argparse.ArgumentParser(prog='praxoryn_mediaops')
    parser.add_argument('--workspace',type=Path,default=Path('./private-output'))
    cmd=parser.add_subparsers(dest='command',required=True)
    for name in ('demo','live'):
        p=cmd.add_parser(name)
        p.add_argument('brief',type=Path)
        if name=='live':
            p.add_argument('--image-workflow',type=Path)
            p.add_argument('--video-workflow',type=Path)
    p=cmd.add_parser('tool')
    p.add_argument('name', choices=['invoice_sum'])
    p.add_argument('values',nargs='+')
    cmd.add_parser('audit')
    args=parser.parse_args(argv)
    if args.command=='demo':
        print(publish(args.brief,args.workspace.resolve(),live=False))
    elif args.command=='live':
        print(publish(args.brief,args.workspace.resolve(),live=True,
              image_workflow=args.image_workflow,video_workflow=args.video_workflow))
    elif args.command=='audit':
        print(json.dumps(show_events(args.workspace/'audit.sqlite'),indent=2))
    elif args.command=='tool':
        print(run_tool(args.name, values=args.values))

if __name__=='__main__':
    main()
