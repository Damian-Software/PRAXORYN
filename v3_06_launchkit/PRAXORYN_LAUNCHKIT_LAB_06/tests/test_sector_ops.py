import unittest
from tools.sector_ops import evaluate
from launchkit.security import Rejected

class SectorOpsTest(unittest.TestCase):
    def test_insurance_missing(self):
        result = evaluate('insurance', {'evidence':[{'id':'incident_form'}]})
        self.assertEqual(len(result['missing_evidence']), 2)
    def test_school_access(self):
        result = evaluate('education', {'role':'guest','resources':[{'id':'a','classification':'public'}, {'id':'b','classification':'staff'}]})
        self.assertEqual(result['visible_resources'], ['a'])
    def test_public_office(self):
        self.assertFalse(evaluate('public_office', {'reference':'a'})['routed'])
    def test_retail_duplicate(self):
        result = evaluate('retail', {'products':[{'sku':'x'},{'sku':'x'}]})
        self.assertEqual(result['duplicate_skus'], ['x'])
    def test_late_delivery(self):
        result = evaluate('logistics', {'deliveries':[{'id':'x','due_utc':'2026-01-01T10:00:00Z','received_utc':'2026-01-01T10:03:00Z'}]})
        self.assertEqual(result['late_deliveries'][0]['seconds_late'], 180)
    def test_health_conflict(self):
        result = evaluate('health_admin', {'appointments':[{'room':'a','starts_at':'x'},{'room':'a','starts_at':'x'}]})
        self.assertEqual(len(result['conflicting_slots']), 1)
    def test_usage_limit(self):
        self.assertTrue(evaluate('ai_provider', {'used_requests':10,'monthly_request_limit':5})['limit_exceeded'])
    def test_bad_scenario(self):
        with self.assertRaises(Rejected):
            evaluate('nonexistent', {})
    def test_accounting(self):
        x=evaluate('accounting', {'rows':[{'quantity':'1','unit_price':'2.00'}],'declared_total':'2.00'})
        self.assertTrue(x['result']['matches'])

if __name__ == '__main__':
    unittest.main()
