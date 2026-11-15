from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import importlib.util
import json
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

def module_at(name, location):
    spec = importlib.util.spec_from_file_location(name, location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

finance = module_at('finance', ROOT / 'finance/invoices.py')
security = module_at('security', ROOT / 'security/triage.py')
review = module_at('review', ROOT / 'developer/review.py')

class FinanceTests(unittest.TestCase):
    def test_totals(self):
        data = finance.calculate([{'description': 'A', 'quantity': '2', 'unit_price': '10.10', 'tax_percent': '21'}])
        self.assertEqual(data['net'], '20.20')
        self.assertEqual(data['tax'], '4.24')
        self.assertEqual(data['gross'], '24.44')
    def test_decimal_is_not_float(self):
        self.assertEqual(finance.money('0.10') + finance.money('0.20'), Decimal('0.30'))
    def test_nan_blocked(self):
        with self.assertRaises(finance.InvoiceError): finance.money('NaN')
    def test_negative_blocked(self):
        with self.assertRaises(finance.InvoiceError): finance.calculate([{'description':'X','quantity':'-1','unit_price':'1','tax_percent':'21'}])
    def test_escaping(self):
        with tempfile.TemporaryDirectory() as folder:
            data = finance.calculate([{'description':'<script>','quantity':'1','unit_price':'2','tax_percent':'0'}])
            paths = finance.write_package(Path(folder), 'A001', data)
            self.assertIn('&lt;script&gt;', paths[1].read_text())
            with self.assertRaises(FileExistsError): finance.write_package(Path(folder), 'A001', data)
    def test_invalid_id(self):
        with self.assertRaises(finance.InvoiceError): finance.write_package(Path('/tmp'), '../escape', {'lines': []})

class SecurityTests(unittest.TestCase):
    def test_dry_run_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'log.jsonl'
            path.write_text('\n'.join(json.dumps({'ts':'2026-01-01T00:00:00Z','event':'auth_failed','ip':'8.8.8.8'}) for _ in range(3)))
            proposal = security.scan(path, 3)
            self.assertEqual(proposal[0]['executed'], False)
            self.assertEqual(len(proposal), 1)
    def test_private_not_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'l'
            path.write_text('\n'.join(json.dumps({'ts':'x','event':'auth_failed','ip':'10.1.1.1'}) for _ in range(5)))
            self.assertEqual(security.scan(path, 3), [])
    def test_invalid_event(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad';p.write_text('{broken\n')
            with self.assertRaises(security.TriageError): security.scan(p)
    def test_bad_threshold(self):
        with self.assertRaises(security.TriageError): security.scan(Path('/tmp/nope'), 1)

class ReviewTests(unittest.TestCase):
    def test_local_only(self):
        with self.assertRaises(review.ReviewError): review.call_existing_api('http://example.org', 'x', {})
    def test_fake_loopback_hostname_rejected(self):
        with self.assertRaises(review.ReviewError):
            review.call_existing_api('http://localhost:8080.evil.example:80', 'x', {})
    def test_diff_from_demo_git(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
            (repo / 'main.py').write_text('x = 1\n')
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'start'], check=True)
            subprocess.run(['git', '-C', str(repo), 'switch', '-qc', 'feature'], check=True)
            (repo / 'main.py').write_text('x = 2\n')
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'change'], check=True)
            self.assertIn('+x = 2', review.prepare_diff(repo, 'main'))
    def test_secret_sentinel(self):
        self.assertTrue(review.SUSPICIOUS.search('+ api_key = secret'))
    def test_payload_is_advisory(self):
        body = review.review_payload('lab-model', 'diff --git a/x b/x')
        self.assertEqual(body['stream'], False)
        self.assertIn('do not issue commands', body['messages'][0]['content'])

if __name__ == '__main__': unittest.main()
