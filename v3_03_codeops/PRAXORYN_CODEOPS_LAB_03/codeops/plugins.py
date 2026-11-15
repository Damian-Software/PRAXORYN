"""Declarative, opt-in literal-token plugins: data, not executed Python code."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .core import Finding, relative

IDENTIFIER = re.compile(r'^[A-Z][A-Z0-9_]{2,49}$')
SEVERITIES = {'low', 'medium', 'high'}


def load_plugin(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or set(obj) != {'id', 'rules'}:
        raise ValueError('Plugin must contain only id and rules')
    if not isinstance(obj['id'], str) or not IDENTIFIER.fullmatch(obj['id']):
        raise ValueError('Invalid plugin id')
    if not isinstance(obj['rules'], list) or len(obj['rules']) > 30:
        raise ValueError('Plugin rules must be a list of at most 30 rules')
    for rule in obj['rules']:
        if not isinstance(rule, dict) or set(rule) != {'id', 'token', 'severity', 'extensions'}:
            raise ValueError('Invalid rule properties')
        if not isinstance(rule['id'], str) or not IDENTIFIER.fullmatch(rule['id']):
            raise ValueError('Invalid rule id')
        if (not isinstance(rule['token'], str) or not 1 <= len(rule['token']) <= 100
                or '\n' in rule['token']):
            raise ValueError('Invalid literal token')
        if rule['severity'] not in SEVERITIES:
            raise ValueError('Invalid severity')
        if (not isinstance(rule['extensions'], list) or not rule['extensions']
                or any(x not in {'.py', '.cpp', '.hpp', '.h'} for x in rule['extensions'])):
            raise ValueError('Invalid extensions')
    return obj


def scan_plugin(plugin: dict, root: Path, files: list[Path]) -> list[Finding]:
    findings = []
    for path in files:
        rel = relative(root, path)
        for lineno, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if len(line) > 1000:
                continue
            for rule in plugin['rules']:
                if path.suffix in rule['extensions'] and rule['token'] in line:
                    findings.append(Finding(rule['id'], rule['severity'], rel, lineno,
                                            f'Found literal token for rule {rule["id"]}',
                                            f'plugin:{plugin["id"]}'))
    return findings
