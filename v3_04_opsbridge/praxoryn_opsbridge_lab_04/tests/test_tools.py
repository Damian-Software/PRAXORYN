import tempfile
import unittest
from pathlib import Path
from tools.invoice_check import check_invoice
from tools.claim_packet import check_claim
from tools.school_acl import allowed
from tools.webhook_verify import sign, verify
from tools.manifest_verify import verify as verify_manifest
import hashlib,json

class ToolsTests(unittest.TestCase):
    def test_invoice(self):
        p=Path('examples/invoice.csv')
        self.assertEqual(check_invoice(p,'309.70')['status'],'matched')
        self.assertEqual(check_invoice(p,'999.00')['status'],'review')
    def test_claim_missing(self):
        r=check_claim({'category':'property','claim_id':'X','document_types':['intake_form']})
        self.assertIn('damage_photos',r['missing_documents'])
        self.assertFalse(r['automated_decision'])
    def test_claim_complete(self):
        r=check_claim({'category':'travel','document_types':['intake_form','travel_confirmation','expense_receipts']})
        self.assertEqual(r['state'],'ready_for_human_review')
    def test_acl_deny(self):
        docs=[{'doc_id':'A','revision':1,'allowed_groups':['teachers']}]
        self.assertEqual(allowed(docs,['students']),[])
        self.assertEqual(len(allowed(docs,['teachers'])),1)
    def test_webhook(self):
        key=b'synthetic-testing-secret'
        sig=sign(b'event',1000,key)
        self.assertTrue(verify(b'event',1000,sig,key,now=1002))
        self.assertFalse(verify(b'changed',1000,sig,key,now=1002))
        self.assertFalse(verify(b'event',1000,sig,key,now=2000))
    def test_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'demo.txt').write_text('demo')
            h=hashlib.sha256(b'demo').hexdigest()
            (p/'manifest.json').write_text(json.dumps({'artifact':'demo.txt','sha256':h}))
            self.assertTrue(verify_manifest(p/'manifest.json'))
            (p/'demo.txt').write_text('changed')
            self.assertFalse(verify_manifest(p/'manifest.json'))
    def test_manifest_escape(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'manifest.json').write_text(json.dumps({'artifact':'../secret','sha256':'0'*64}))
            with self.assertRaises(ValueError):verify_manifest(p/'manifest.json')

if __name__=='__main__':unittest.main()
