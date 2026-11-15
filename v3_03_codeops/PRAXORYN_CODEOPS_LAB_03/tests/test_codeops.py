import json
import tempfile
import unittest
from pathlib import Path
from codeops.cli import main
from codeops.core import project_files
from codeops.llm import explain_findings
from codeops.plugins import load_plugin, scan_plugin
from codeops.scanners import python_builtin

ROOT = Path(__file__).resolve().parents[1]

class ScanTests(unittest.TestCase):
    def test_fixture_builtin_findings(self):
        items = python_builtin(ROOT / 'examples/demo_repo/unsafe.py', ROOT / 'examples/demo_repo')
        codes = {f.rule for f in items}
        self.assertTrue({'PY_DYNAMIC_EXEC','PY_SHELL_TRUE','PY_BARE_EXCEPT'} <= codes)

    def test_syntax_error(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); f = root / 'broken.py'; f.write_text('def broken(:\n')
            self.assertEqual(python_builtin(f,root)[0].rule,'PY_SYNTAX')

    def test_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); (root/'ok.py').write_text('print(1)')
            (root/'link.py').symlink_to(root/'ok.py')
            self.assertEqual([x.name for x in project_files(root)], ['ok.py'])

    def test_plugin_valid_and_findings(self):
        plugin=load_plugin(ROOT/'plugins/review_tokens.json')
        root=ROOT/'examples/demo_repo'
        issues=scan_plugin(plugin, root,project_files(root))
        self.assertEqual({f.rule for f in issues}, {'PY_DEBUG_BREAKPOINT','CPP_DEBUG_PRINT'})

    def test_plugin_schema_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.json';p.write_text('{"id":"RUN","rules":[{"id":"X","token":"x","severity":"fatal","extensions":[".py"]}]}')
            with self.assertRaises(ValueError):load_plugin(p)

    def test_loopback_only_for_model(self):
        with self.assertRaises(ValueError):explain_findings([], 'https://remote.example/v1', 'x')

    def test_cli_makes_reports(self):
        with tempfile.TemporaryDirectory() as t:
            output=Path(t)/'reports'
            status=main(['scan','--project',str(ROOT/'examples/demo_repo'),
                         '--output',str(output),'--plugin',str(ROOT/'plugins/review_tokens.json')])
            self.assertEqual(status,0)
            for name in ('report.json','report.html','report.sarif'):
                self.assertTrue((output/name).is_file())
            self.assertGreater(json.loads((output/'report.json').read_text())['high_count'],0)

    def test_quality_gate_fails(self):
        with tempfile.TemporaryDirectory() as t:
            status=main(['scan','--project',str(ROOT/'examples/demo_repo'),
                         '--output',str(Path(t)/'reports'),'--ci'])
            self.assertEqual(status,1)

    def test_required_tool_must_be_ok(self):
        with tempfile.TemporaryDirectory() as t:
            status=main(['scan','--project',str(ROOT/'examples/demo_repo'),
                         '--output',str(Path(t)/'reports'),'--require-tools','never-installed'])
            self.assertEqual(status,2)

    def test_no_external_code_execution(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); (root/'bad.py').write_text('raise RuntimeError("not executed")\n')
            status=main(['scan','--project',str(root),'--output',str(root/'reports')])
            self.assertEqual(status,0)

if __name__=='__main__':unittest.main()
