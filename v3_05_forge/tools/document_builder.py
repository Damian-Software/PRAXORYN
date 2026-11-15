"""Convert a reviewed, tenant-scoped result into DOCX and optionally PDF.

Requires python-docx for DOCX and installed LibreOffice for PDF. No Docker.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path


def build_docx(reviewed:Path,output_dir:Path):
    from docx import Document
    from docx.shared import Cm,Pt
    data=json.loads(reviewed.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError('Expected result object')
    output_dir.mkdir(parents=True,exist_ok=True)
    doc=Document()
    doc.add_heading('Reviewed Local AI Result',0)
    doc.add_paragraph('This document is a human-reviewed artifact. Confirm the source before distribution.')
    for key,value in sorted(data.items()):
        doc.add_heading(str(key)[:80],2)
        doc.add_paragraph(json.dumps(value,ensure_ascii=False,indent=2)[:15000])
    out=output_dir/'reviewed-result.docx'
    if out.exists():raise FileExistsError(out)
    doc.save(out)
    return out


def pdf_from_docx(docx:Path,output_dir:Path)->Path:
    if not shutil.which('libreoffice'):
        raise RuntimeError('Install LibreOffice or omit --pdf')
    subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/praxoryn-forge-doc',
                    '--headless','--convert-to','pdf','--outdir',str(output_dir),str(docx)],
                   check=True,timeout=80,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out=output_dir/(docx.stem+'.pdf')
    if not out.exists():raise RuntimeError('PDF was not created')
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('reviewed',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pdf',action='store_true')
    a=p.parse_args();docx=build_docx(a.reviewed,a.output)
    print(docx)
    if a.pdf:print(pdf_from_docx(docx,a.output))

if __name__=='__main__':main()
