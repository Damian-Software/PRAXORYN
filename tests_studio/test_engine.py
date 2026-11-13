"""Offline tests; real AI GPU generation is not part of this test suite."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from praxoryn_studio.engine import (initialize, submit, list_jobs, get_job,
    validate_tenant, approve, export, JobError, run_one)

class ValidationTests(unittest.TestCase):
    def test_tenant_validation(self):
        self.assertEqual(validate_tenant('demo_school'), 'demo_school')
        for x in ('../etc', 'A', 'x y', '/tmp', 'UPPERCASE', ''):
            with self.assertRaises(ValueError): validate_tenant(x)
    def test_prompt_length_and_kind(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            initialize(home)
            with self.assertRaises(ValueError):submit(home,'tenant_a','arbitrary','hello')
            with self.assertRaises(ValueError):submit(home,'tenant_a','report','')
            with self.assertRaises(ValueError):submit(home,'tenant_a','report','x'*4001)
    def test_cross_tenant_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);initialize(home)
            key=submit(home,'tenant_a','report','Write a synthetic report')
            self.assertEqual(len(list_jobs(home,'tenant_a')),1)
            self.assertEqual(len(list_jobs(home,'tenant_b')),0)
            with self.assertRaises(JobError):get_job(home,'tenant_b',key)
    def test_cannot_approve_before_review(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);initialize(home)
            key=submit(home,'tenant_a','report','Write a synthetic report')
            with self.assertRaises(JobError):approve(home,'tenant_a',key,'reviewer01')
            with self.assertRaises(JobError):export(home,'tenant_a',key)

class WorkerTests(unittest.TestCase):
    def test_offline_worker_approval_export(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);initialize(home)
            key=submit(home,'tenant_a','report','Prepare a fictional quarterly report')
            self.assertEqual(run_one(home),key)
            self.assertEqual(get_job(home,'tenant_a',key)['status'],'review')
            self.assertEqual(run_one(home),None)
            approve(home,'tenant_a',key,'reviewer01')
            archive=export(home,'tenant_a',key)
            self.assertTrue(archive.exists())
            self.assertEqual(get_job(home,'tenant_a',key)['status'],'exported')
            from zipfile import ZipFile
            with ZipFile(archive) as z:
                self.assertIn('report.pdf',z.namelist())
                self.assertIn('manifest.json',z.namelist())
            with self.assertRaises(JobError):approve(home,'tenant_a',key,'reviewer01')

if __name__=='__main__':unittest.main()
