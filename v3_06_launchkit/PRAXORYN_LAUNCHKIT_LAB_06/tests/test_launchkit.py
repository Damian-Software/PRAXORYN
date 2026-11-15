"""Offline tests: no GPU, model server, or customer data required."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from launchkit import db
from launchkit.artifacts import verify_result
from launchkit.security import Rejected, slug
from launchkit.worker import process_one
from launchkit.workflows import run, invoice_check, python_review
from launchkit.api import create_handler

class LaunchKitTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = db.open_db(self.root)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_key_scope(self):
        secret = db.create_client(self.db, "alpha", "submit", "uploader")
        self.assertTrue(secret.startswith("pxr_"))
        self.assertEqual(db.authenticate(self.db, secret)["tenant"], "alpha")
        self.assertIsNone(db.authenticate(self.db, "pxr_wrong"))

    def test_idempotency(self):
        first, was_new = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        second, again = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        self.assertTrue(was_new)
        self.assertFalse(again)
        self.assertEqual(first, second)

    def test_reused_idempotency_rejected(self):
        db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        with self.assertRaises(Rejected):
            db.submit(self.db, "alpha", "memo", {"note": "Other note"}, "case001")

    def test_tenant_separation(self):
        identifier, _ = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        self.assertIsNone(db.get_job(self.db, "bravo", identifier))
        self.assertEqual(len(db.list_jobs(self.db, "bravo")), 0)

    def test_worker_and_artifacts(self):
        identifier, _ = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        self.assertEqual(process_one(self.root)["status"], "review")
        self.assertTrue(verify_result(self.root, "alpha", identifier))

    def test_approval(self):
        identifier, _ = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        process_one(self.root)
        db.approve(self.db, "alpha", identifier, "reviewer01")
        self.assertEqual(db.get_job(self.db, "alpha", identifier)["status"], "approved")

    def test_no_cross_tenant_approval(self):
        identifier, _ = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        process_one(self.root)
        with self.assertRaises(Rejected):
            db.approve(self.db, "bravo", identifier, "reviewer01")

    def test_audit_chain(self):
        db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        self.assertTrue(db.audit_health(self.db)[0])
        self.db.execute("UPDATE audit SET action='altered' WHERE seq=1")
        self.assertFalse(db.audit_health(self.db)[0])

    def test_invoice_math(self):
        x = invoice_check({"rows": [{"quantity": "3", "unit_price": "12.35"}], "declared_total": "37.05"})
        self.assertTrue(x["matches"])
        self.assertEqual(x["calculated_total"], "37.05")

    def test_invoice_mismatch(self):
        x = invoice_check({"rows": [{"quantity": "3", "unit_price": "12.35"}], "declared_total": "37.04"})
        self.assertFalse(x["matches"])

    def test_python_findings(self):
        x = python_review({"code": "value = eval('1 + 1')\n"})
        self.assertEqual(x["findings"][0]["rule"], "PY-EVAL")

    def test_python_syntax(self):
        x = python_review({"code": "def oops(\n"})
        self.assertEqual(x["findings"][0]["rule"], "PY-SYNTAX")

    def test_no_fake_media(self):
        x = run("media_plan", {"asset_type": "video", "prompt": "Create an approved clip"})
        self.assertEqual(x["status"], "plan_only")

    def test_reject_invalid_tenant(self):
        with self.assertRaises(Rejected):
            slug("../../secret")

    def test_reject_bad_json_money(self):
        with self.assertRaises(Rejected):
            invoice_check({"rows": [{"quantity": "NaN", "unit_price": "12"}], "declared_total": "0"})

    def test_worker_failure(self):
        identifier, _ = db.submit(self.db, "alpha", "memo", {"note": "a"}, "case001")
        self.assertEqual(process_one(self.root)["status"], "failed")
        self.assertEqual(db.get_job(self.db, "alpha", identifier)["status"], "failed")

    def test_artifact_tampering(self):
        identifier, _ = db.submit(self.db, "alpha", "memo", {"note": "Synthetic note"}, "case001")
        process_one(self.root)
        path = self.root / "artifacts" / "alpha" / identifier / "result.json"
        path.write_text("tampered")
        self.assertFalse(verify_result(self.root, "alpha", identifier))

if __name__ == "__main__":
    unittest.main()
