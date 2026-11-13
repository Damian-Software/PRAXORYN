"""JSON, SARIF, and escaped HTML reports for human approval."""
from __future__ import annotations
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from .core import Finding

LEVELS = {'critical': 'error', 'high': 'error', 'medium': 'warning', 'low': 'note'}


def write_reports(output: Path, findings: list[Finding], tools: dict[str, str]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    ordered = sorted(findings, key=lambda f: (f.path, f.line, f.rule))
    report = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
              'tool_status': tools, 'findings': [f.to_dict() for f in ordered],
              'finding_count': len(ordered),
              'high_count': sum(f.severity in {'high', 'critical'} for f in ordered)}
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    sarif_results = []
    for f in ordered:
        sarif_results.append({
            'ruleId': f.rule, 'level': LEVELS[f.severity], 'message': {'text': f.message},
            'locations': [{'physicalLocation': {'artifactLocation': {'uri': f.path},
                                               'region': {'startLine': f.line,
                                                          'startColumn': f.column}}}]})
    sarif = {'version': '2.1.0', '$schema':
             'https://json.schemastore.org/sarif-2.1.0.json',
             'runs': [{'tool': {'driver': {'name': 'Praxoryn CodeOps', 'rules': []}},
                       'results': sarif_results}]}
    (output / 'report.sarif').write_text(json.dumps(sarif, indent=2), encoding='utf-8')
    rows = []
    for f in ordered:
        cols = [f.severity, f.rule, f.path, str(f.line), f.message, f.source]
        rows.append('<tr>' + ''.join('<td>' + html.escape(col) + '</td>' for col in cols) + '</tr>')
    status = ', '.join(f'{html.escape(k)}: {html.escape(v)}' for k, v in tools.items())
    page = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>CodeOps Review</title><style>body{font:16px system-ui;max-width:1100px;'
            'margin:3rem auto;padding:0 1rem;color:#21313b}table{border-collapse:collapse;'
            'width:100%}td,th{border:1px solid #abc;padding:.5rem;text-align:left}'
            'th{background:#edf4f6}tr:nth-child(even){background:#f7fafb}</style>'
            f'<h1>CodeOps report</h1><p>Findings: {len(ordered)}</p><p>{status}</p>'
            '<table><thead><tr><th>Severity</th><th>Rule</th><th>File</th>'
            '<th>Line</th><th>Message</th><th>Source</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></html>')
    (output / 'report.html').write_text(page, encoding='utf-8')
