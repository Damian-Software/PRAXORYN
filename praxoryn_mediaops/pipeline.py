"""Explicit demonstration/live workflow with one user-authorized output directory."""
from __future__ import annotations
import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from .security import validate_brief, safe_name
from .media import preview_image, still_to_video
from .documents import make_docx, make_pdf
from .llm import chat
from .comfy import submit_and_collect
from .audit import log_event


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(brief_path: Path, root: Path, *, live: bool = False,
            image_workflow: Path | None = None, video_workflow: Path | None = None) -> Path:
    brief = validate_brief(json.loads(brief_path.read_text(encoding='utf-8')))
    root.mkdir(parents=True, exist_ok=True)
    slug = safe_name(brief['title'])
    folder = root / slug
    if folder.exists():
        raise FileExistsError(f'Output already exists: {folder} (use a new title)')
    folder.mkdir(mode=0o700)
    try:
        if live:
            base = os.environ.get('PRAXORYN_MODEL_URL','http://127.0.0.1:8080')
            model = os.environ.get('PRAXORYN_MODEL_ID','')
            if not model:
                raise ValueError('Set PRAXORYN_MODEL_ID for live mode')
            text = chat(brief['prompt'], base_url=base, model=model)
        else:
            text = ('OFFLINE DEMO ONLY. This is synthetic placeholder text; no AI model was called.\n\n'
                    'Business purpose: ' + brief['kind'] + '.\n\n'
                    'Replace this passage after reviewing the live model output.')
        (folder/'draft.txt').write_text(text, encoding='utf-8')
        if live and image_workflow:
            flow=json.loads(image_workflow.read_text(encoding='utf-8'))
            assets=submit_and_collect(base_url=os.environ.get('PRAXORYN_COMFY_URL','http://127.0.0.1:8188'),
                      workflow=flow,node=os.environ.get('PRAXORYN_COMFY_TEXT_NODE',''),
                      field=os.environ.get('PRAXORYN_COMFY_TEXT_FIELD','text'),
                      prompt=brief['prompt'],destination=folder)
            image = next((p for p in assets if p.suffix.lower() in ('.png','.jpg','.jpeg')),None)
        else:
            image=preview_image(folder/'preview.png',brief['title'])
        docx=make_docx(brief['title'],text,image,folder/'report.docx')
        pdf=make_pdf(docx,folder)
        if live and video_workflow:
            vf=json.loads(video_workflow.read_text(encoding='utf-8'))
            submit_and_collect(base_url=os.environ.get('PRAXORYN_COMFY_URL','http://127.0.0.1:8188'),
                workflow=vf,node=os.environ.get('PRAXORYN_COMFY_VIDEO_NODE',''),
                field=os.environ.get('PRAXORYN_COMFY_VIDEO_FIELD','text'),
                prompt=brief['prompt'],destination=folder)
        else:
            if image and image.suffix.lower() in ('.png','.jpg','.jpeg'):
                still_to_video(image,folder/'still-preview.mp4')
        artifacts=[]
        for f in sorted(folder.iterdir()):
            if f.is_file():
                artifacts.append({'file':f.name,'sha256':_hash(f),'bytes':f.stat().st_size})
        manifest={'mode':'live' if live else 'offline-demo',
                  'created_at':datetime.now(timezone.utc).isoformat(),
                  'source_brief':brief_path.name,'artifacts':artifacts,
                  'notice':'All outputs require human review before publication.'}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        log_event(root/'audit.sqlite','live' if live else 'demo','ok',len(artifacts))
        return folder
    except Exception:
        log_event(root/'audit.sqlite','live' if live else 'demo','error')
        raise
