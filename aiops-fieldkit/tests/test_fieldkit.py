import os
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from aiops.finance import amount,check_invoice_csv
from aiops.codecheck import scan_python_file
from aiops.guard import propose_from_jsonl
from aiops.report import build_html
from aiops.core import read_workspace_file,safe_write
from aiops import store
from aiops.inference import local_chat

ROOT=pathlib.Path(__file__).resolve().parents[1]

class FinanceTests(unittest.TestCase):
    def test_decimal(self):self.assertEqual(str(amount('1.005')), '1.01')
    def test_non_finite(self):
        with self.assertRaises(ValueError):amount('NaN')
    def test_invoice_mismatch(self):
        output=check_invoice_csv(str(ROOT/'examples/invoice_lines.csv'))
        self.assertEqual(output['rows'],3)
        self.assertEqual(output['issues'][0]['issue'],'line_mismatch')
        self.assertEqual(output['expected_totals']['INV-001'],'119.00')

class ScanTests(unittest.TestCase):
    def test_static_alerts(self):
        output=scan_python_file(str(ROOT/'examples/unsafe_sample.py'))
        self.assertEqual({x['rule'] for x in output},{'dynamic-evaluation','shell-true'})
    def test_syntax_error(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'broken.py';p.write_text('def fn(:\n')
            self.assertEqual(scan_python_file(str(p))[0]['rule'],'syntax-error')
    def test_no_code_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'do_not_run.py';marker=pathlib.Path(d)/'marker'
            p.write_text(f"open({str(marker)!r},'w').write('bad')\n")
            scan_python_file(str(p));self.assertFalse(marker.exists())

class GuardTests(unittest.TestCase):
    def test_alerts_global(self):
        output=propose_from_jsonl(str(ROOT/'examples/access.jsonl'), threshold=4)
        self.assertEqual(len(output),1)
        self.assertEqual(output[0]['ip'],'8.8.8.8')
    def test_reject_invalid_threshold(self):
        with self.assertRaises(ValueError):propose_from_jsonl(str(ROOT/'examples/access.jsonl'), 0)

class FileTests(unittest.TestCase):
    def test_allowed_file(self):
        payload,hash_value=read_workspace_file(str(ROOT/'examples'),'support_request.txt')
        self.assertTrue(payload.startswith(b'A customer'))
        self.assertEqual(len(hash_value),64)
    def test_path_traversal(self):
        with self.assertRaises(ValueError):read_workspace_file(str(ROOT/'examples'),'../tests/test_fieldkit.py')
    def test_symlink_not_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);(p/'target.txt').write_text('test');(p/'link.txt').symlink_to(p/'target.txt')
            with self.assertRaises(ValueError):read_workspace_file(d,'link.txt')
    def test_atomic_export(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(pathlib.Path(d)/'a.txt');safe_write(path,b'hello');self.assertEqual(pathlib.Path(path).read_bytes(),b'hello')

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=store.connect(str(pathlib.Path(self.tmp.name)/'test.db'))
        store.init(self.db);store.create_tenant(self.db,'org-alpha',5);store.create_tenant(self.db,'org-beta',3)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_tenant_scoped_idempotency(self):
        first=store.submit(self.db,'org-alpha','summary','hello world','request-1234')
        self.assertEqual(first,store.submit(self.db,'org-alpha','summary','changed','request-1234'))
        other=store.submit(self.db,'org-beta','summary','hello','request-1234')
        self.assertNotEqual(first,other)
        self.assertEqual(self.db.execute("SELECT credit FROM tenants WHERE tenant_id='org-alpha'").fetchone()[0],4)
    def test_no_credit(self):
        store.create_tenant(self.db,'empty',0)
        with self.assertRaises(ValueError):store.submit(self.db,'empty','summary','test','request-empty')
    def test_approval_requires_review(self):
        job=store.submit(self.db,'org-alpha','summary','hello','request-review')
        with self.assertRaises(ValueError):store.decide(self.db,'org-alpha',job,'lead',True)
        leased=store.lease_one(self.db);self.assertEqual(leased['id'],job)
        store.complete(self.db,job,'draft')
        store.decide(self.db,'org-alpha',job,'lead',True)
        self.assertEqual(store.get_job(self.db,'org-alpha',job)['state'],'approved')
    def test_tenant_isolation(self):
        job=store.submit(self.db,'org-alpha','reply','private','request-private')
        self.assertIsNone(store.get_job(self.db,'org-beta',job))
        store.lease_one(self.db);store.complete(self.db,job,'response')
        with self.assertRaises(ValueError):store.decide(self.db,'org-beta',job,'admin',True)
    def test_worker_failure_refunds(self):
        job=store.submit(self.db,'org-alpha','summary','hello','request-fail')
        self.assertEqual(self.db.execute("SELECT credit FROM tenants WHERE tenant_id='org-alpha'").fetchone()[0],4)
        store.lease_one(self.db);store.complete(self.db,job,'',False)
        self.assertEqual(self.db.execute("SELECT credit FROM tenants WHERE tenant_id='org-alpha'").fetchone()[0],5)
    def test_rejects_invalid_idempotency(self):
        with self.assertRaises(ValueError):store.submit(self.db,'org-alpha','summary','hello','x')

class ApiTests(unittest.TestCase):
    def test_no_nonlocal_url(self):
        with patch.dict(os.environ,{'AI_BASE_URL':'https://example.com','AI_MODEL':'some-model'}):
            with self.assertRaises(ValueError):local_chat('hello')
    def test_missing_model(self):
        with patch.dict(os.environ,{'AI_BASE_URL':'http://127.0.0.1:8080','AI_MODEL':''}):
            with self.assertRaises(ValueError):local_chat('hello')
    def test_escape_html(self):
        rendered=build_html('<X>',[{'id':1,'kind':'summary','state':'approved','draft':'<script>alert(1)</script>'}])
        self.assertIn('&lt;script&gt;',rendered)
        self.assertNotIn('<script>',rendered)

if __name__=='__main__':unittest.main()
