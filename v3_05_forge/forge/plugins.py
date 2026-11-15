"""Fixed, auditable plugin registry. A manifest never grants shell access."""
from __future__ import annotations
import ast
import csv
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .files import checked_input,digest_file
from .model import generate_text

VALID_KINDS={'invoice','code','brief','media_plan','evidence'}


def read_manifest(root: Path, name: str) -> dict:
    if not re.fullmatch(r'[a-z][a-z0-9_]{1,39}',name):
        raise ValueError('Invalid plugin identifier')
    path=root/f'{name}.json'
    if path.is_symlink() or not path.is_file():
        raise ValueError('Plugin manifest missing or linked')
    obj=json.loads(path.read_text(encoding='utf-8'))
    if set(obj) != {'id','kind','version','description'}:
        raise ValueError('Plugin manifest fields do not match schema')
    if obj['id']!=name or obj['kind'] not in VALID_KINDS:
        raise ValueError('Unrecognized plugin')
    if not isinstance(obj['version'],str) or len(obj['version'])>30:
        raise ValueError('Invalid plugin version')
    return obj


def run_invoice(inputs: Path, payload: dict) -> dict:
    path=checked_input(inputs,str(payload.get('filename','')))
    if path.suffix!='.csv':raise ValueError('Invoice input must be CSV')
    total=Decimal('0')
    lines=0
    with path.open('r',encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=['item','quantity','unit_price']:
            raise ValueError('Expected CSV headers item,quantity,unit_price')
        for row in reader:
            if lines>=5000:raise ValueError('Too many invoice rows')
            try:
                qty=Decimal(row['quantity']); price=Decimal(row['unit_price'])
                if not qty.is_finite() or not price.is_finite() or qty<0 or price<0:
                    raise ValueError('Invalid numeric value')
            except (InvalidOperation,TypeError) as exc:
                raise ValueError(f'Bad line at row {lines+2}') from exc
            total+=(qty*price).quantize(Decimal('0.01'))
            lines+=1
    expected=Decimal(str(payload.get('expected_total','0')))
    if not expected.is_finite():raise ValueError('Expected total must be finite')
    return {'status':'matched' if total==expected else 'review_needed',
            'calculated_total':str(total.quantize(Decimal('0.01'))),
            'expected_total':str(expected.quantize(Decimal('0.01'))),
            'rows':lines,'source_sha256':digest_file(path),
            'note':'Accounting review aid, not an accounting decision'}


def run_code(inputs: Path, payload: dict) -> dict:
    path=checked_input(inputs,str(payload.get('filename','')))
    if path.suffix not in {'.py','.cpp','.h','.hpp'}:
        raise ValueError('Use Python or C++ source')
    source=path.read_text(encoding='utf-8')
    issues=[]
    if path.suffix=='.py':
        try:root=ast.parse(source,filename=path.name)
        except SyntaxError as exc:
            issues.append({'line':exc.lineno,'rule':'PY_PARSE','severity':'error','message':'Python syntax invalid'})
        else:
            for node in ast.walk(root):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'eval','exec'}:
                    issues.append({'line':node.lineno,'rule':'PY_DYNAMIC_EXEC','severity':'warning',
                                   'message':'Manual review required for dynamic execution'})
    else:
        for line_no,line in enumerate(source.splitlines(),1):
            if re.search(r'\bgets\s*\(',line):
                issues.append({'line':line_no,'rule':'CPP_GETS','severity':'warning','message':'Review unsafe legacy input function'})
    return {'status':'review_needed' if issues else 'no_heuristic_findings',
            'issues':issues,'source_sha256':digest_file(path),
            'note':'Heuristics do not replace compiler, Ruff, clang-tidy or security audit'}


def run_brief(inputs: Path, payload: dict, backend:str) -> dict:
    text=str(payload.get('prompt',''))
    if not (5<=len(text)<=4000):raise ValueError('Prompt must contain 5-4000 characters')
    draft, provider=generate_text(text,backend)
    return {'status':'draft_only','text':draft,'backend':provider,'note':'Human approval required'}


def run_media_plan(inputs: Path, payload: dict) -> dict:
    # Workflow plans contain no executable code and never invoke ComfyUI on their own.
    title=str(payload.get('title',''))
    if not (2<=len(title)<=120):raise ValueError('Title length must be 2-120')
    return {'status':'planning_only',
            'steps':['Approve brief','Run existing image workflow','Inspect image',
                     'Run existing video workflow','Inspect frames and sound',
                     'Render PDF/DOCX','Obtain final human approval'],
            'title':title,'note':'No AI media generation was performed'}


def run_evidence(inputs: Path,payload:dict) -> dict:
    path=checked_input(inputs,str(payload.get('filename','')))
    if path.suffix not in {'.txt','.md'}:raise ValueError('Evidence requires .txt or .md')
    text=path.read_text(encoding='utf-8')
    terms=[str(x).strip() for x in payload.get('terms',[]) if isinstance(x,str)]
    if len(terms)>10 or any(len(x)>60 for x in terms):raise ValueError('Invalid search terms')
    lines=[]
    for i,line in enumerate(text.splitlines(),1):
        if any(t.casefold() in line.casefold() for t in terms):
            lines.append({'line':i,'excerpt':line[:240]})
        if len(lines)>=20:break
    return {'status':'evidence_candidates','matches':lines,'source_sha256':digest_file(path),
            'note':'Candidate passages; check the source document before relying on them'}


RUNNERS={'invoice':run_invoice,'code':run_code,'brief':run_brief,'media_plan':run_media_plan,'evidence':run_evidence}


def execute(inputs:Path,payload:dict,kind:str,backend:str) -> dict:
    if kind not in RUNNERS:raise ValueError('Unsupported kind')
    if kind=='brief':return run_brief(inputs,payload,backend)
    return RUNNERS[kind](inputs,payload)
