import unittest
from decimal import Decimal
from pathlib import Path
from praxoryn_mediaops.plugins import invoice_sum, catalog_lookup, run_tool

class PluginTests(unittest.TestCase):
    def test_decimal(self):self.assertEqual(invoice_sum(['1.10','2.20']), '3.30')
    def test_negative(self):self.assertEqual(invoice_sum(['1.10','-2.20']),'-1.10')
    def test_invalid(self):
        with self.assertRaises(ValueError): invoice_sum(['oops'])
    def test_nonfinite(self):
        with self.assertRaises(ValueError): invoice_sum(['NaN'])
    def test_denied(self):
        with self.assertRaises(PermissionError): run_tool('shell',cmd='rm -rf /')
    def test_catalog(self):
        csv=Path(__file__).parents[1]/'examples'/'catalog.csv'
        self.assertEqual(catalog_lookup(csv,'DEMO-001')['price'],'59.00')
    def test_not_found(self):
        csv=Path(__file__).parents[1]/'examples'/'catalog.csv'
        self.assertIsNone(catalog_lookup(csv,'MISSING'))
