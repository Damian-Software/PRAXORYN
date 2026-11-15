import json
import tempfile
import unittest
from pathlib import Path
from praxoryn_studio.tools import invoice_totals,code_review,claim_inventory,index_markdown,search_markdown

ROOT=Path(__file__).resolve().parents[1]/'examples'/'studio'
class ToolTests(unittest.TestCase):
    def test_invoice(self):
        result=invoice_totals(ROOT/'invoices.csv')
        self.assertEqual(result['total'],'3030.20')
    def test_invoice_rejects_nan(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.csv';p.write_text('reference,quantity,unit_price,currency\nx,NaN,9,CZK\n')
            with self.assertRaises(ValueError):invoice_totals(p)
    def test_code_review(self):
        result=code_review(ROOT/'review_sample.py')
        self.assertEqual([x['code'] for x in result['findings']],['DYNAMIC_EXECUTION','BARE_EXCEPT'])
    def test_claim_inventory(self):
        result=claim_inventory(ROOT/'claim.json')
        self.assertEqual(result['missing_documents'],['policy_reference'])
        self.assertEqual(result['decision'],'HUMAN_REVIEW_REQUIRED')
    def test_fts_search(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'fts.sqlite'
            index_markdown([ROOT/'manual_one.md',ROOT/'manual_two.md'],db)
            self.assertEqual(search_markdown(db,'administrator')['matches'][0]['source'],'manual_two.md')
    def test_fts_rejects_query_operators(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'fts.sqlite'
            index_markdown([ROOT/'manual_one.md'],db)
            with self.assertRaises(ValueError):search_markdown(db,'" OR *')
if __name__=='__main__':unittest.main()
