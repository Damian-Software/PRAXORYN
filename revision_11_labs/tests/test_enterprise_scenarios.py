import hashlib
import json
import sqlite3
import unittest
from decimal import Decimal
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from invoice_check import inspect_invoice, money
from review_gate import evaluate
from tenant_ledger import connect, reserve, reverse, verify_key
from document_acl import authorize_document, filter_documents
from claim_triage import prepare_review
from sales_draft import prepare_message

BASE = Path(__file__).resolve().parents[1] / 'fixtures'


class InvoiceChecks(unittest.TestCase):
    def test_valid(self):
        data = json.loads((BASE/'invoice_ok.json').read_text())
        self.assertEqual(inspect_invoice(data)['status'], 'CHECKED')
    def test_mismatch(self):
        data = json.loads((BASE/'invoice_bad.json').read_text())
        self.assertEqual(inspect_invoice(data)['issues'], ['amount_mismatch'])
    def test_reject_float(self):
        with self.assertRaises(ValueError): money(0.1)
    def test_reject_nan(self):
        with self.assertRaises(ValueError): money('NaN')
    def test_rounding(self):
        self.assertEqual(money('10.05'), Decimal('10.05'))
    def test_missing_field(self):
        self.assertEqual(inspect_invoice({})['status'], 'REVIEW')
    def test_bad_line(self):
        self.assertEqual(inspect_invoice({'invoice_id':'A','currency':'EUR','lines':[{}],'declared_total':'1.00'})['status'], 'REVIEW')
    def test_negative(self):
        self.assertEqual(inspect_invoice({'invoice_id':'A','currency':'EUR','lines':[{'quantity':'1','unit_price':'-1'}], 'declared_total':'0'})['status'], 'REVIEW')
    def test_rounding_half_even(self):
        self.assertEqual(inspect_invoice({'invoice_id':'A','currency':'EUR','lines':[{'quantity':'0.33','unit_price':'0.15'}], 'declared_total':'0.05'})['status'], 'CHECKED')


class ReviewGateChecks(unittest.TestCase):
    def test_pass(self): self.assertEqual(evaluate(json.loads((BASE/'code_checks_pass.json').read_text()))['decision'], 'PASS')
    def test_fail(self): self.assertEqual(evaluate(json.loads((BASE/'code_checks_fail.json').read_text()))['decision'], 'BLOCK')
    def test_missing(self): self.assertEqual(evaluate({})['reasons'], ['missing_checks'])
    def test_ai_cannot_override(self): self.assertIn('ai_cannot_override_required_checks', evaluate(json.loads((BASE/'code_checks_fail.json').read_text()))['reasons'])
    def test_invalid_structure(self): self.assertEqual(evaluate({'checks': []})['decision'], 'BLOCK')


class TenantLedgerChecks(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.db.execute('INSERT INTO tenants VALUES (?,?,?)', ('tenant-A', 300, 0))
        self.db.execute('INSERT INTO tenants VALUES (?,?,?)', ('tenant-B', 400, 0))
    def tearDown(self): self.db.close()
    def test_reserve(self): self.assertEqual(reserve(self.db, 'tenant-A','r1',200), 'RESERVED')
    def test_quota(self): self.assertEqual(reserve(self.db, 'tenant-A','r1',301), 'REJECTED_QUOTA')
    def test_idempotency(self):
        reserve(self.db, 'tenant-A','r1',200)
        self.assertEqual(reserve(self.db, 'tenant-A','r1',200),'DUPLICATE')
        self.assertEqual(self.db.execute("SELECT used_tokens FROM tenants WHERE tenant_id='tenant-A'").fetchone()[0],200)
    def test_idempotency_conflict(self):
        reserve(self.db, 'tenant-A','r1',200)
        self.assertEqual(reserve(self.db, 'tenant-A','r1',201),'REJECTED_IDEMPOTENCY')
    def test_tenant_separation(self):
        reserve(self.db, 'tenant-A','same',200)
        self.assertEqual(reserve(self.db, 'tenant-B','same',100),'RESERVED')
    def test_reverse(self):
        reserve(self.db, 'tenant-A','r1',200)
        self.assertEqual(reverse(self.db,'tenant-A','r1'),'REVERSED')
        self.assertEqual(self.db.execute("SELECT used_tokens FROM tenants WHERE tenant_id='tenant-A'").fetchone()[0],0)
    def test_reverse_twice(self):
        reserve(self.db,'tenant-A','r1',200)
        reverse(self.db,'tenant-A','r1')
        self.assertEqual(reverse(self.db,'tenant-A','r1'),'UNCHANGED')
    def test_reject_boolean_token(self): self.assertEqual(reserve(self.db, 'tenant-A','r1',True),'REJECTED_INPUT')
    def test_reject_unknown_tenant(self): self.assertEqual(reserve(self.db, 'tenant-C','r1',1),'REJECTED_QUOTA')
    def test_api_key_digest(self):
        hashed=hashlib.sha256(b'token-demo-only').hexdigest()
        self.assertTrue(verify_key('token-demo-only',hashed))
        self.assertFalse(verify_key('other',hashed))


class DocumentsAndClaims(unittest.TestCase):
    def setUp(self):
        self.principal={'active':True,'tenant_id':'school-A','subject_id':'teacher-1','roles':['teacher'], 'educational_interest':True}
        self.document={'tenant_id':'school-A','allowed_roles':['teacher'], 'sensitivity':'student_record'}
    def test_teacher(self): self.assertTrue(authorize_document(self.principal,self.document))
    def test_no_interest(self):
        self.principal['educational_interest']=False
        self.assertFalse(authorize_document(self.principal,self.document))
    def test_other_tenant(self):
        self.document['tenant_id']='school-B'
        self.assertFalse(authorize_document(self.principal,self.document))
    def test_inactive(self):
        self.principal['active']=False
        self.assertFalse(authorize_document(self.principal,self.document))
    def test_unassigned_case(self):
        doc={'tenant_id':'school-A','allowed_roles':['teacher'],'sensitivity':'restricted_case','case_id':'c1'}
        self.assertFalse(authorize_document(self.principal,doc))
    def test_assigned_case(self):
        self.principal['assigned_case_ids']=['c1']
        doc={'tenant_id':'school-A','allowed_roles':['teacher'],'sensitivity':'restricted_case','case_id':'c1'}
        self.assertTrue(authorize_document(self.principal,doc))
    def test_filter(self):
        self.assertEqual(len(filter_documents(self.principal,[self.document,dict(self.document,tenant_id='school-B')])),1)
    def test_claim_supported(self):
        claim={'state':'received','document_ids':['doc-01']}
        suggestion={'evidence_ids':['doc-01'],'confidence':0.99}
        self.assertEqual(prepare_review(claim,suggestion)['decision'],'HUMAN_REVIEW')
    def test_claim_outside_case(self):
        self.assertEqual(prepare_review({'state':'received','document_ids':['d1']},{'evidence_ids':['other']})['decision'],'REVIEW')
    def test_claim_no_evidence(self):
        self.assertEqual(prepare_review({'state':'received','document_ids':[]}, {'evidence_ids':[]})['decision'],'REVIEW')
    def test_claim_finalized(self):
        self.assertEqual(prepare_review({'state':'paid','document_ids':['d1']},{'evidence_ids':['d1']})['decision'],'REJECT')
    def test_sales_opt_out(self):
        self.assertEqual(prepare_message({'id':'L1','opt_out':True,'approved_contact':True},'Hello')['state'],'BLOCK')
    def test_sales_review(self):
        self.assertEqual(prepare_message({'id':'L1','opt_out':False,'approved_contact':True},'Hello')['state'],'REVIEW_REQUIRED')
    def test_sales_missing_permission(self):
        self.assertEqual(prepare_message({'id':'L1','opt_out':False},'Hello')['state'],'BLOCK')


if __name__ == '__main__': unittest.main()

class FailClosedRegressions(unittest.TestCase):
    def test_unknown_sensitivity_denied(self):
        self.assertFalse(authorize_document({'active':True,'tenant_id':'a','subject_id':'u','roles':['staff']},
                    {'tenant_id':'a','allowed_roles':['staff'],'sensitivity':'unknown'}))
    def test_bad_case_assignment_type_denied(self):
        principal={'active':True,'tenant_id':'a','subject_id':'u','roles':['staff'], 'assigned_case_ids':'case-11'}
        record={'tenant_id':'a','allowed_roles':['staff'],'sensitivity':'restricted_case','case_id':'case-1'}
        self.assertFalse(authorize_document(principal,record))
    def test_allowed_school_documents(self):
        from school_demo import run_demo
        ids=run_demo()
        self.assertEqual(ids,['math_basics','teachers_guide','student_demo_record'])
    def test_school_other_tenant_blocked(self):
        from school_demo import run_demo
        self.assertNotIn('other_school',run_demo())
