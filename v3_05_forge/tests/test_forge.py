import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from forge.store import open_db,submit,claim,complete,review,get_job,events
from forge.files import checked_input,safe_output_dir
from forge.model import validate_base_url,generate_text
from forge.plugins import execute,read_manifest
from forge.__main__ import run_once

ROOT=Path(__file__).resolve().parent.parent

class ForgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.inp=self.home/'inputs';self.inp.mkdir()
        self.res=self.home/'results';self.res.mkdir()
        self.con=open_db(self.home/'db.sqlite')
        for name in ('invoice.csv','sample.py','sample.cpp','policy.txt'):
            shutil.copy(ROOT/'examples'/name,self.inp/name)
    def tearDown(self):
        self.con.close();self.tmp.cleanup()
    def test_submission_and_tenant_isolation(self):
        a=submit(self.con,'school','invoice',{'filename':'invoice.csv'},'school-a-001')
        self.assertEqual(a['state'],'queued')
        with self.assertRaises(LookupError):get_job(self.con,'insurer',a['id'])
    def test_idempotency_returns_same_job(self):
        a=submit(self.con,'a','code',{'filename':'sample.py'},'idem-001')
        b=submit(self.con,'a','code',{'filename':'sample.py'},'idem-001')
        self.assertEqual(a['id'],b['id'])
    def test_idempotency_detects_changed_payload(self):
        submit(self.con,'a','code',{'filename':'sample.py'},'idem-002')
        with self.assertRaises(ValueError):submit(self.con,'a','code',{'filename':'sample.cpp'},'idem-002')
    def test_worker_only_waits_for_review(self):
        a=submit(self.con,'a','invoice',{'filename':'invoice.csv','expected_total':'45.50'},'idem-003')
        result=run_once(self.con,self.home,'offline')
        self.assertEqual(result['status'],'waiting_review')
        self.assertEqual(get_job(self.con,'a',a['id'])['state'],'waiting_review')
        review(self.con,'a',a['id'],'approved','analyst-1')
        self.assertEqual(get_job(self.con,'a',a['id'])['state'],'approved')
    def test_cannot_review_other_tenant(self):
        a=submit(self.con,'a','invoice',{'filename':'invoice.csv'},'idem-004')
        run_once(self.con,self.home,'offline')
        with self.assertRaises(LookupError):review(self.con,'b',a['id'],'approved','analyst')
    def test_no_direct_approval(self):
        a=submit(self.con,'a','invoice',{'filename':'invoice.csv'},'idem-005')
        row=claim(self.con)
        with self.assertRaises(ValueError):complete(self.con,'a',a['id'],{},'approved')
    def test_invoice_exact_decimal(self):
        result=execute(self.inp,{'filename':'invoice.csv','expected_total':'45.50'},'invoice','offline')
        self.assertEqual(result['status'],'matched')
        self.assertEqual(result['calculated_total'],'45.50')
    def test_invoice_mismatch_is_review(self):
        result=execute(self.inp,{'filename':'invoice.csv','expected_total':'45.51'},'invoice','offline')
        self.assertEqual(result['status'],'review_needed')
    def test_python_dynamic_exec_finding(self):
        result=execute(self.inp,{'filename':'sample.py'},'code','offline')
        self.assertEqual(result['issues'][0]['rule'],'PY_DYNAMIC_EXEC')
    def test_cpp_scan(self):
        result=execute(self.inp,{'filename':'sample.cpp'},'code','offline')
        self.assertEqual(result['status'],'no_heuristic_findings')
    def test_evidence_line_numbers(self):
        result=execute(self.inp,{'filename':'policy.txt','terms':['audit']},'evidence','offline')
        self.assertEqual(result['matches'][0]['line'],3)
    def test_media_does_not_claim_generation(self):
        result=execute(self.inp,{'title':'Marketing example'},'media_plan','offline')
        self.assertEqual(result['status'],'planning_only')
    def test_offline_model_admits_demo(self):
        txt,mode=generate_text('Write training note','offline')
        self.assertIn('OFFLINE DEMO',txt)
        self.assertEqual(mode,'offline')
    def test_loopback_validation(self):
        self.assertEqual(validate_base_url('http://127.0.0.1:8080/v1'),'http://127.0.0.1:8080/v1')
        for url in ('http://example.com:8080/v1','https://127.0.0.1:8080/v1','http://127.0.0.1:80/v1',
                    'http://127.0.0.1:8080/private','http://user:pass@127.0.0.1:8080/v1'):
            with self.subTest(url=url),self.assertRaises(ValueError):validate_base_url(url)
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):checked_input(self.inp,'../policy.txt')
    def test_symlinks_rejected(self):
        (self.inp/'link.txt').symlink_to(self.inp/'policy.txt')
        with self.assertRaises(ValueError):checked_input(self.inp,'link.txt')
    def test_plugin_manifest_schema(self):
        m=read_manifest(ROOT/'plugins','invoice');self.assertEqual(m['kind'],'invoice')
    def test_audit_redacts_payload(self):
        a=submit(self.con,'a','brief',{'prompt':'private customer data example'},'idem-006')
        event_dump=json.dumps(events(self.con,'a'))
        self.assertNotIn('private customer data',event_dump)
    def test_invalid_tenant_rejected(self):
        with self.assertRaises(ValueError):submit(self.con,'../x','invoice',{},'idem-007')
    def test_queue_empty(self):
        self.assertEqual(run_once(self.con,self.home,'offline')['status'],'empty')
    def test_failed_invalid_input_metadata_only(self):
        a=submit(self.con,'a','invoice',{'filename':'missing.csv'},'idem-008')
        result=run_once(self.con,self.home,'offline')
        self.assertEqual(result['status'],'failed')
        self.assertEqual(get_job(self.con,'a',a['id'])['state'],'failed')
    def test_workflow_output_sha(self):
        a=submit(self.con,'a','brief',{'prompt':'Create synthetic sample notice'},'idem-009')
        run_once(self.con,self.home,'offline')
        r=json.loads(get_job(self.con,'a',a['id'])['result_json'])
        self.assertEqual(len(r['sha256']),64)
        self.assertTrue(Path(r['file']).is_file())

if __name__=='__main__':unittest.main()
