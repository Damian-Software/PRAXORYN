"""Small, auditable deterministic tools for sector-oriented exercises."""
from __future__ import annotations
import argparse
import ast
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3


def invoice_totals(path: Path) -> dict:
    """Totals are verified using decimal arithmetic, never model-generated numbers."""
    rows=[]
    grand=Decimal('0.00')
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        required={'reference','quantity','unit_price','currency'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('missing required columns')
        for idx,row in enumerate(reader,start=2):
            try:
                quantity=Decimal(row['quantity'])
                price=Decimal(row['unit_price'])
            except (InvalidOperation,TypeError):
                raise ValueError(f'non-numeric amount at CSV row {idx}') from None
            if not quantity.is_finite() or not price.is_finite() or quantity<0 or price<0:
                raise ValueError(f'invalid amount at CSV row {idx}')
            if row['currency']!='CZK':
                raise ValueError('mixed currencies require a separate FX policy')
            subtotal=(quantity*price).quantize(Decimal('0.01'))
            grand+=subtotal
            rows.append({'reference':row['reference'],'subtotal':str(subtotal)})
            if len(rows)>1000:raise ValueError('too many lines')
    return {'currency':'CZK','line_totals':rows,'total':str(grand)}


def code_review(path: Path) -> dict:
    """A deliberately small AST guard, not a security scanner or test runner."""
    data=path.read_text(encoding='utf-8')
    if len(data)>250_000:raise ValueError('source exceeds lab limit')
    tree=ast.parse(data,filename=path.name)
    findings=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            if isinstance(node.func,ast.Name) and node.func.id in {'eval','exec'}:
                findings.append({'line':node.lineno,'code':'DYNAMIC_EXECUTION'})
            if isinstance(node.func,ast.Attribute) and node.func.attr in {'run','Popen','call'}:
                for kw in node.keywords:
                    if kw.arg=='shell' and isinstance(kw.value,ast.Constant) and kw.value.value is True:
                        findings.append({'line':node.lineno,'code':'SHELL_TRUE_REVIEW'})
        if isinstance(node,ast.ExceptHandler) and node.type is None:
            findings.append({'line':node.lineno,'code':'BARE_EXCEPT'})
    return {'file':path.name,'findings':sorted(findings,key=lambda x:x['line'])}


def claim_inventory(path: Path) -> dict:
    """Check completeness only; do not infer entitlement or fraud."""
    payload=json.loads(path.read_text(encoding='utf-8'))
    required={'claim_id','evidence'}
    if not isinstance(payload,dict) or not required.issubset(payload):
        raise ValueError('invalid claim file')
    available=payload['evidence']
    if not isinstance(available,list) or any(not isinstance(x,str) for x in available):
        raise ValueError('evidence must be a list of strings')
    expected=('incident_report','policy_reference','contact_record')
    missing=[x for x in expected if x not in available]
    return {'claim_id':payload['claim_id'],'missing_documents':missing,
            'decision':'HUMAN_REVIEW_REQUIRED'}


def index_markdown(files: list[Path], destination: Path) -> dict:
    """A tiny FTS5 exercise with synthetic/approved Markdown only."""
    if len(files)>50:raise ValueError('too many documents')
    destination.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(destination)
    try:
        con.execute('CREATE VIRTUAL TABLE IF NOT EXISTS snippets USING fts5(source, body)')
        con.execute('DELETE FROM snippets')
        added=0
        for file in files:
            body=file.read_text(encoding='utf-8')
            if len(body)>20_000:raise ValueError('document too long')
            # The path is never returned as an arbitrary network location.
            for i in range(0,len(body),1000):
                con.execute('INSERT INTO snippets(source,body) VALUES(?,?)',(file.name,body[i:i+1000]))
                added+=1
        con.commit()
        return {'indexed_chunks':added,'files':len(files)}
    finally:
        con.close()


def search_markdown(destination: Path, words: str) -> dict:
    # Quoted tokens avoid passing untrusted FTS query syntax to MATCH.
    tokens=words.split()
    if not 1<=len(tokens)<=5 or any(not x.isalnum() or len(x)>40 for x in tokens):
        raise ValueError('query must contain 1..5 simple terms')
    query=' AND '.join('"'+x+'"' for x in tokens)
    con=sqlite3.connect(destination)
    try:
        rows=con.execute('SELECT source,substr(body,1,400) FROM snippets '
                         'WHERE snippets MATCH ? LIMIT 5',(query,)).fetchall()
        return {'matches':[{'source':source,'excerpt':excerpt} for source,excerpt in rows]}
    finally:con.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description='PRAXORYN deterministic sector toolkit')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('invoice','review','claim'):
        cmd=sub.add_parser(name);cmd.add_argument('file',type=Path)
    ix=sub.add_parser('index');ix.add_argument('--db',required=True,type=Path);ix.add_argument('files',nargs='+',type=Path)
    search=sub.add_parser('search');search.add_argument('--db',required=True,type=Path);search.add_argument('query')
    args=parser.parse_args(argv)
    if args.command=='invoice':result=invoice_totals(args.file)
    elif args.command=='review':result=code_review(args.file)
    elif args.command=='claim':result=claim_inventory(args.file)
    elif args.command=='index':result=index_markdown(args.files,args.db)
    else:result=search_markdown(args.db,args.query)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
