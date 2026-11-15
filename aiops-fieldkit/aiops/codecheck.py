"""Static Python AST checks. Never executes inspected code."""
from __future__ import annotations
import ast
import pathlib

RULES = {
    "eval": "dynamic-evaluation",
    "exec": "dynamic-execution",
    "pickle.loads": "unsafe-deserialization",
    "os.system": "shell-command",
}


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _name(node.value) + "." + node.attr
    return ""


def scan_python_file(path: str) -> list[dict]:
    source = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [{"line": exc.lineno or 0, "rule": "syntax-error", "detail": str(exc.msg)}]
    alerts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = _name(node.func)
            if callee in RULES:
                alerts.append({"line": node.lineno, "rule": RULES[callee], "detail": callee})
            if callee in {"subprocess.run", "subprocess.Popen", "subprocess.call"}:
                if any(key.arg == "shell" and isinstance(key.value, ast.Constant) and key.value.value is True for key in node.keywords):
                    alerts.append({"line": node.lineno, "rule": "shell-true", "detail": callee})
    return sorted(alerts, key=lambda item: (item["line"], item["rule"]))
