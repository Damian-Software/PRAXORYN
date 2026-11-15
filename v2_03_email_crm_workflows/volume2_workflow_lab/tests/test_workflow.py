import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / 'app' / 'workflow.py'
spec = importlib.util.spec_from_file_location('workflow', APP)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inbox = self.root / 'inbox'
        self.inbox.mkdir()
        self.conn = w.db_connect(self.root / 'state.db')
        self.addCleanup(self.conn.close)
        w.initialize(self.conn)
        self.data = (b'From: demo@example.invalid\nSubject: Test issue\n'
                     b'Content-Type: text/plain; charset="utf-8"\n\nPlease help.\n')
        (self.inbox / 'test.eml').write_bytes(self.data)

    def import_once(self):
        return w.ingest_email(self.conn, self.inbox / 'test.eml', self.inbox)

    def test_mail_import_and_idempotency(self):
        self.assertEqual(self.import_once(), 'added')
        self.assertEqual(self.import_once(), 'duplicate')
        self.assertEqual(len(w.display(self.conn)), 1)

    def test_symlink_rejected(self):
        (self.inbox / 'shortcut.eml').symlink_to(self.inbox / 'test.eml')
        with self.assertRaises(ValueError):
            w.ingest_email(self.conn, self.inbox / 'shortcut.eml', self.inbox)

    def test_nonapproved_directory_rejected(self):
        outside = self.root / 'outside.eml'
        outside.write_bytes(self.data)
        with self.assertRaises(ValueError):
            w.ingest_email(self.conn, outside, self.inbox)

    def test_oversized_file_rejected(self):
        (self.inbox / 'big.eml').write_bytes(b'x' * (w.MAX_FILE + 1))
        with self.assertRaises(ValueError):
            w.ingest_email(self.conn, self.inbox / 'big.eml', self.inbox)

    def test_html_only_rejected(self):
        with self.assertRaises(ValueError):
            w.parse_email(b'From: a@example.invalid\nContent-Type: text/html\n\nHi')

    def test_claim_single_worker(self):
        self.import_once()
        first = w.claim(self.conn)
        self.assertEqual(first['status'], 'leased')
        self.assertIsNone(w.claim(self.conn))

    def test_offline_draft_and_review(self):
        self.import_once()
        job = w.claim(self.conn)
        draft = w.generate_draft(job, True, '', '', '')
        w.complete(self.conn, job, draft)
        self.assertEqual(w.display(self.conn)[0]['status'], 'review')

    def test_expired_token_rejected(self):
        self.import_once()
        job = w.claim(self.conn)
        with self.assertRaises(RuntimeError):
            w.complete(self.conn, dict(job, lease_id='wrong'), 'Draft')

    def test_approval_needs_review(self):
        self.import_once()
        with self.assertRaises(ValueError):
            w.transition(self.conn, 1, 'approved', 'review', 'operator-01')

    def test_approval_must_name_actor(self):
        self.import_once()
        job = w.claim(self.conn)
        w.complete(self.conn, job, 'Draft')
        with self.assertRaises(ValueError):
            w.transition(self.conn, 1, 'approved', 'review', 'a')

    def test_export_requires_approval(self):
        self.import_once()
        with self.assertRaises(ValueError):
            w.export_eml(self.conn, 1, self.root / 'outbox', 'operator-01')

    def test_export_eml_after_review(self):
        self.import_once()
        job = w.claim(self.conn)
        w.complete(self.conn, job, 'Reviewed answer')
        w.transition(self.conn, 1, 'approved', 'review', 'reviewer-01')
        result = w.export_eml(self.conn, 1, self.root / 'outbox', 'reviewer-01')
        self.assertIn(b'Reviewed answer', result.read_bytes())
        self.assertEqual(w.display(self.conn)[0]['status'], 'exported')

    def test_retry_then_dead_letter(self):
        self.import_once()
        job = w.claim(self.conn)
        w.fail_job(self.conn, job, 'upstream')
        self.assertEqual(w.display(self.conn)[0]['status'], 'ready')
        self.conn.execute('UPDATE jobs SET next_run=0 WHERE id=1')
        job = w.claim(self.conn)
        w.fail_job(self.conn, job, 'upstream')
        self.conn.execute('UPDATE jobs SET next_run=0 WHERE id=1')
        job = w.claim(self.conn)
        w.fail_job(self.conn, job, 'upstream')
        self.assertEqual(w.display(self.conn)[0]['status'], 'failed')

    def test_csv_import(self):
        p = self.inbox / 'tickets.csv'
        p.write_text('customer_id,subject,details\nA-1,Access,Reset token\n', encoding='utf8')
        self.assertEqual(w.ingest_csv(self.conn, p, self.inbox), ['added'])
        self.assertEqual(w.ingest_csv(self.conn, p, self.inbox), ['duplicate'])

    def test_csv_does_not_export_email(self):
        p = self.inbox / 'tickets.csv'
        p.write_text('customer_id,subject,details\nA-1,Access,Reset token\n')
        w.ingest_csv(self.conn, p, self.inbox)
        job = w.claim(self.conn)
        w.complete(self.conn, job, 'Draft')
        w.transition(self.conn, 1, 'approved', 'review', 'reviewer-01')
        with self.assertRaises(ValueError):
            w.export_eml(self.conn, 1, self.root / 'outbox', 'reviewer-01')

    def test_audit_excludes_body(self):
        self.import_once()
        job = w.claim(self.conn)
        w.complete(self.conn, job, 'Draft')
        rows = [dict(x) for x in self.conn.execute('SELECT * FROM audit')]
        self.assertNotIn('Please help', str(rows))


if __name__ == '__main__':
    unittest.main()
