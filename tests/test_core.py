import json
import tempfile
import unittest
from pathlib import Path
from opsbridge.core import open_db, create_job, claim_job, complete_job, transition, verify_audit, path_under, clean_tenant
from opsbridge.adapters import local_base, comfy_submit
from opsbridge.worker import run_one

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=open_db(self.root)
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def test_lifecycle(self):
        job=create_job(self.db,'demo_acme','summary',{'text':'A. B.'})
        self.assertEqual(run_one(self.db,self.root),job)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0],'review')
        transition(self.db,job,'review','approved','reviewer01')
        transition(self.db,job,'approved','released','publisher01')
        ok,_=verify_audit(self.db);self.assertTrue(ok)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0],'released')
    def test_no_double_claim(self):
        create_job(self.db,'demo_acme','summary',{'text':'Test'})
        self.assertIsNotNone(claim_job(self.db))
        self.assertIsNone(claim_job(self.db))
    def test_unknown_tenant(self):
        with self.assertRaises(ValueError):clean_tenant('../bad')
    def test_escape_path(self):
        with self.assertRaises(ValueError):path_under(self.root,'..','different')
    def test_large_input(self):
        with self.assertRaises(ValueError):create_job(self.db,'demo_acme','summary',{'text':'x'*25000})
    def test_tamper(self):
        create_job(self.db,'demo_acme','document',{'title':'T'})
        self.db.execute("UPDATE audit SET detail_code='modified' WHERE event_id=1")
        ok,bad=verify_audit(self.db)
        self.assertFalse(ok);self.assertEqual(bad,1)
    def test_bad_transition(self):
        job=create_job(self.db,'demo_acme','summary',{'text':'X'})
        with self.assertRaises(ValueError):transition(self.db,job,'review','approved','x')
    def test_code_fixture(self):
        job=create_job(self.db,'demo_acme','code_review',{'source':'eval(a)'})
        run_one(self.db,self.root)
        row=self.db.execute('SELECT output_path FROM jobs WHERE job_id=?',(job,)).fetchone()
        self.assertIn('DEMO_EVAL',Path(row[0]).read_text())
    def test_reject_redirect(self):
        for u in ['https://example.com', 'http://169.254.169.254/x', 'file:///etc/passwd']:
            with self.assertRaises(ValueError):local_base(u)
    def test_reject_comfy_empty(self):
        with self.assertRaises(ValueError):comfy_submit('http://127.0.0.1:8188',{})

if __name__=='__main__':unittest.main()
