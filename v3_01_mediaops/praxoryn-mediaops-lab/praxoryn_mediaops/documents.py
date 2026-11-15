"""Create an editable DOCX and optionally export PDF via LibreOffice."""
from __future__ import annotations
from pathlib import Path
import subprocess
from docx import Document
from docx.shared import Cm, Pt, RGBColor


def make_docx(title: str, text: str, image: Path | None, target: Path) -> Path:
    doc = Document()
    sec=doc.sections[0]
    sec.top_margin=Cm(2);sec.bottom_margin=Cm(2)
    doc.styles['Normal'].font.name='DejaVu Sans'
    doc.styles['Normal'].font.size=Pt(11)
    doc.add_heading(title, 0)
    for paragraph in text.split('\n\n'):
        if paragraph.strip():
            doc.add_paragraph(paragraph.strip())
    if image and image.is_file():
        doc.add_picture(str(image), width=Cm(15))
        doc.add_paragraph('Figure 1. Visual asset.',style='Caption')
    doc.add_heading('Review before publication', 2)
    doc.add_paragraph('Check facts, licensing, personal data, and accessibility before external release.')
    doc.core_properties.author='Damián Zelený'
    doc.save(target)
    return target


def make_pdf(docx: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    profile=target_dir/'.lo-profile'
    subprocess.run(['libreoffice',f'-env:UserInstallation=file://{profile.resolve()}',
                   '--headless','--convert-to','pdf','--outdir',str(target_dir),str(docx)],
                   check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pdf=target_dir/(docx.stem+'.pdf')
    if not pdf.is_file() or pdf.read_bytes()[:5] != b'%PDF-':
        raise RuntimeError('PDF export failed')
    return pdf
