"""Command-line entry point; intentionally does not execute project tests or patches."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .core import project_files
from .llm import explain_findings
from .plugins import load_plugin, scan_plugin
from .reporting import write_reports
from .scanners import python_builtin, run_clang_tidy, run_ruff


def scan(args: argparse.Namespace) -> int:
    root = Path(args.project).resolve(strict=True)
    output = Path(args.output).resolve()
    if output == root or root in output.parents and output.name != 'reports':
        raise ValueError('Choose an output directory separate from project sources')
    files = project_files(root)
    findings = []
    for path in files:
        if path.suffix == '.py':
            findings.extend(python_builtin(path, root))
    ruff, ruff_status = run_ruff(root, files)
    clang, clang_status = run_clang_tidy(root, files)
    findings.extend(ruff)
    findings.extend(clang)
    tools = {'python-ast': 'ok', 'ruff': ruff_status, 'clang-tidy': clang_status}
    if args.plugin:
        definition = load_plugin(Path(args.plugin))
        findings.extend(scan_plugin(definition, root, files))
        tools[f'plugin:{definition["id"]}'] = 'ok'
    write_reports(output, findings, tools)
    if args.model:
        try:
            notes = explain_findings([f.to_dict() for f in findings], args.base_url, args.model)
            (output / 'model_review.md').write_text(notes, encoding='utf-8')
            tools['model'] = 'ok'
        except Exception as exc:
            tools['model'] = f'failed: {type(exc).__name__}'
            (output / 'model_review_error.txt').write_text(str(exc), encoding='utf-8')
        write_reports(output, findings, tools)
    print(f'Files: {len(files)}; findings: {len(findings)}; report: {output}')
    print('Analyzers: ' + json.dumps(tools, ensure_ascii=False))
    unavailable = [x for x in args.require_tools.split(',') if x and tools.get(x) != 'ok']
    if unavailable:
        print('Required analyzers unavailable: ' + ', '.join(unavailable), file=sys.stderr)
        return 2
    return 1 if args.ci and any(f.severity in ('high', 'critical') for f in findings) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='codeops')
    sub = parser.add_subparsers(dest='command', required=True)
    sc = sub.add_parser('scan', help='Offline-first scan of a local project')
    sc.add_argument('--project', required=True)
    sc.add_argument('--output', required=True)
    sc.add_argument('--plugin', default='')
    sc.add_argument('--model', default='', help='Existing local model id; optional')
    sc.add_argument('--base-url', default='http://127.0.0.1:8080/v1')
    sc.add_argument('--require-tools', default='', help='Comma-separated analyzer names')
    sc.add_argument('--ci', action='store_true', help='Exit 1 on high severity findings')
    args = parser.parse_args(argv)
    try:
        return scan(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'Configuration error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
