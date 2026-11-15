"""Conservative built-in checks and optional established analyzers."""
from __future__ import annotations
import ast
import json
import re
import shutil
import subprocess
from pathlib import Path
from .core import Finding, relative


def python_builtin(path: Path, root: Path) -> list[Finding]:
    source = path.read_text(encoding='utf-8', errors='replace')
    rel = relative(root, path)
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as err:
        return [Finding('PY_SYNTAX', 'high', rel, err.lineno or 1,
                        err.msg, 'python-ast', err.offset or 1)]
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(Finding('PY_BARE_EXCEPT', 'medium', rel,
                                  node.lineno, 'Bare except may hide errors', 'python-ast'))
        if not isinstance(node, ast.Call):
            continue
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            name = f'{node.func.value.id}.{node.func.attr}'
        if name in {'eval', 'exec'}:
            issues.append(Finding('PY_DYNAMIC_EXEC', 'high', rel, node.lineno,
                                  'Dynamic code execution requires review', 'python-ast'))
        elif name == 'pickle.loads':
            issues.append(Finding('PY_PICKLE_LOADS', 'high', rel, node.lineno,
                                  'Avoid deserializing untrusted pickle input', 'python-ast'))
        elif name in {'subprocess.run', 'subprocess.call', 'subprocess.Popen'}:
            if any(k.arg == 'shell' and isinstance(k.value, ast.Constant)
                   and k.value.value is True for k in node.keywords):
                issues.append(Finding('PY_SHELL_TRUE', 'high', rel, node.lineno,
                                      'Shell invocation needs explicit justification', 'python-ast'))
    return issues


def run_ruff(root: Path, files: list[Path], timeout: int = 45) -> tuple[list[Finding], str]:
    if not shutil.which('ruff'):
        return [], 'not_installed'
    py_files = [p for p in files if p.suffix == '.py']
    if not py_files:
        return [], 'no_python_files'
    cmd = ['ruff', 'check', '--no-cache', '--output-format', 'json',
           '--no-respect-gitignore', *[str(p) for p in py_files]]
    try:
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return [], f'failed: {type(exc).__name__}'
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [], f'failed: Ruff output is not JSON (exit {result.returncode})'
    if result.returncode not in (0, 1):
        return [], f'failed: Ruff exited {result.returncode}'
    issues = []
    for row in data:
        location = row.get('location', {})
        filename = Path(row.get('filename', ''))
        try:
            rel = relative(root, filename.resolve())
        except ValueError:
            continue
        issues.append(Finding('RUFF_' + str(row.get('code', 'UNKNOWN')), 'medium', rel,
                              int(location.get('row', 1)), str(row.get('message', '')), 'ruff',
                              int(location.get('column', 1))))
    return issues, 'ok'


CLANG_LINE = re.compile(r'^(.*?):(\d+):(\d+):\s*(warning|error):\s*(.*?)\s*(?:\[([^]]+)\])?$')


def run_clang_tidy(root: Path, files: list[Path], timeout: int = 60) -> tuple[list[Finding], str]:
    cpp_files = [p for p in files if p.suffix in {'.cpp', '.cc', '.cxx'}]
    if not cpp_files:
        return [], 'no_cpp_files'
    if not shutil.which('clang-tidy'):
        return [], 'not_installed'
    build = root / 'build'
    if not (build / 'compile_commands.json').is_file():
        return [], 'missing_compile_commands'
    findings = []
    for path in cpp_files:
        cmd = ['clang-tidy', '-p', str(build), str(path)]
        try:
            result = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                    timeout=timeout, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return findings, f'failed: {type(exc).__name__}'
        for line in (result.stdout + '\n' + result.stderr).splitlines():
            match = CLANG_LINE.match(line.strip())
            if not match:
                continue
            filename, row, col, level, msg, rule = match.groups()
            file_path = Path(filename)
            try:
                rel = relative(root, file_path.resolve())
            except ValueError:
                continue
            findings.append(Finding('CLANG_' + (rule or level).upper(),
                                    'high' if level == 'error' else 'medium',
                                    rel, int(row), msg, 'clang-tidy', int(col)))
        # clang-tidy may exit non-zero due to compiler diagnostics, which are included above.
        if result.returncode and not findings:
            return findings, f'failed: clang-tidy exited {result.returncode}'
    return findings, 'ok'
