import json
import tempfile
import unittest
from pathlib import Path
from tools.comfy_bridge import origin,load_api_workflow
from tools.sarif_export import export_sarif
from tools.document_builder import build_docx

class ToolTests(unittest.TestCase):
    def test_comfy_origin(self):
        self.assertEqual(origin('http://127.0.0.1:8188'),'http://127.0.0.1:8188')
    def test_comfy_rejects_external_origin(self):
        for url in ('https://127.0.0.1:8188','http://example.com:8188','http://127.0.0.1:8188/api'):
            with self.assertRaises(ValueError):origin(url)
    def test_workflow_dry_run_shape(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'flow.json';p.write_text('{"5":{"class_type":"Test","inputs":{}}}')
            self.assertEqual(len(load_api_workflow(p)),1)
    def test_sarif(self):
        result=export_sarif({'issues':[{'line':4,'rule':'PY_DYNAMIC_EXEC','severity':'warning','message':'Review'}]},'a.py')
        self.assertEqual(result['version'],'2.1.0')
        self.assertEqual(result['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region']['startLine'],4)
    def test_document_builder(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json';p.write_text('{"status":"approved"}')
            out=build_docx(p,Path(d)/'output')
            self.assertTrue(out.is_file())

if __name__=='__main__':unittest.main()
