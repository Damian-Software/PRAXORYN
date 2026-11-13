import unittest
from pathlib import Path
from praxoryn_mediaops.security import safe_name,validate_brief,must_be_inside

class SecurityTests(unittest.TestCase):
    def test_slug(self): self.assertEqual(safe_name('Report 2026'), 'Report-2026')
    def test_traversal(self): self.assertEqual(safe_name('../../etc/passwd'), 'etc-passwd')
    def test_invalid_slug(self):
        with self.assertRaises(ValueError): safe_name('---')
    def test_title_required(self):
        with self.assertRaises(ValueError): validate_brief({'title':'','prompt':'abc'})
    def test_prompt_required(self):
        with self.assertRaises(ValueError): validate_brief({'title':'abc','prompt':''})
    def test_invalid_kind(self):
        with self.assertRaises(ValueError): validate_brief({'title':'abc','prompt':'x','kind':'hack'})
    def test_brief_ok(self): self.assertEqual(validate_brief({'title':'x','prompt':'abc'})['kind'],'internal')
    def test_within(self): self.assertEqual(must_be_inside(Path('/tmp'), 'demo'),Path('/tmp/demo'))
