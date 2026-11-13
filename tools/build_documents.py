#!/usr/bin/env python3
"""Generate a plain-language DOCX from approved JSON; optionally convert to PDF."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile


def build(source: pathlib.Path, out: pathlib.Path) -> dict:
    from docx import Document
    from docx.shared import Pt, Cm
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("title"), str):
        raise ValueError("Document JSON requires title")
    if not isinstance(data.get("sections"), list) or len(data["sections"]) > 20:
        raise ValueError("Document JSON requires at most 20 sections")
    d = Document()
    sec = d.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(2)
    d.styles["Normal"].font.name = "DejaVu Sans"
    d.styles["Normal"].font.size = Pt(10)
    d.add_heading(data["title"][:160], level=0)
    d.add_paragraph("Status: draft - manual approval required")
    for section in data["sections"]:
        if not isinstance(section, dict):
            raise ValueError("Section must be an object")
        title, body = section.get("heading"), section.get("body")
        if not isinstance(title, str) or not isinstance(body, str) or len(body) > 10000:
            raise ValueError("Invalid document section")
        d.add_heading(title[:160], level=1)
        d.add_paragraph(body)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(out)
    raw = out.read_bytes()
    return {"docx": str(out), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def convert_pdf(docx: pathlib.Path) -> pathlib.Path:
    command = shutil.which("libreoffice")
    if not command:
        raise RuntimeError("LibreOffice is not installed")
    with tempfile.TemporaryDirectory(prefix="praxoryn-lo-") as profile:
        uri = pathlib.Path(profile).as_uri()
        result = subprocess.run([command, "-env:UserInstallation=" + uri,
                                 "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                timeout=90, check=False)
    target = docx.with_suffix(".pdf")
    if result.returncode != 0 or not target.is_file() or not target.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("PDF conversion failed; inspect local LibreOffice logs")
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source"); p.add_argument("docx"); p.add_argument("--pdf", action="store_true")
    args = p.parse_args()
    out = pathlib.Path(args.docx)
    result = build(pathlib.Path(args.source), out)
    if args.pdf:
        result["pdf"] = str(convert_pdf(out))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
