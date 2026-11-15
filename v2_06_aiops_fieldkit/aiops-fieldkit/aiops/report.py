"""Produce escaped, offline HTML report with no external assets."""
from __future__ import annotations
from html import escape
import json
from pathlib import Path
from .core import safe_write


def build_html(title: str, items: list[dict]) -> str:
    rows=[]
    for item in items:
        cells=''.join('<td>'+escape(str(item.get(key, '')))+ '</td>' for key in ('id','kind','state','draft'))
        rows.append('<tr>'+cells+'</tr>')
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>"+escape(title)+"</title><style>body{font:16px system-ui;margin:3rem auto;max-width:80rem;padding:0 1rem}"
            "table{width:100%;border-collapse:collapse}th,td{border:1px solid #789;padding:.5rem;text-align:left;vertical-align:top}"
            "td{overflow-wrap:anywhere}</style><h1>"+escape(title)+"</h1>"
            "<table><thead><tr><th>ID</th><th>Kind</th><th>State</th><th>Draft</th></tr></thead><tbody>"
            +''.join(rows)+"</tbody></table></html>")


def write_html(path: str, title: str, items: list[dict]):
    safe_write(path, build_html(title, items).encode('utf-8'))
