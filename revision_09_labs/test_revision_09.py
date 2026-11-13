"""Deterministic offline tests for volume I, revision 0.9."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from slo import calculate_slo
from admission import AdmissionController
from recovery import assess_recovery_point
from release_gate import evaluate_gate
from manifest import build_manifest, verify_manifest, manifest_json


class SLOTests(unittest.TestCase):
    def test_expected_budget(self):
        result = calculate_slo(100_000, 99_950, "0.999")
        self.assertEqual(result.error_budget, 100)
        self.assertEqual(result.remaining_budget, 50)
        self.assertEqual(result.status, "pass")

    def test_budget_exceeded(self):
        self.assertEqual(calculate_slo(100_000, 99_899, "0.999").status, "fail")

    def test_no_data(self):
        result = calculate_slo(0, 0)
        self.assertEqual(result.status, "no_data")
        self.assertIsNone(result.availability)

    def test_full_target(self):
        self.assertEqual(calculate_slo(10, 10, "1").status, "pass")
        self.assertEqual(calculate_slo(10, 9, "1").status, "fail")

    def test_negative_count(self):
        with self.assertRaises(ValueError): calculate_slo(-1, 0)

    def test_invalid_success_count(self):
        with self.assertRaises(ValueError): calculate_slo(3, 4)

    def test_float_counts_refused(self):
        with self.assertRaises(TypeError): calculate_slo(1.5, 1)

    def test_nonfinite_target(self):
        with self.assertRaises(ValueError): calculate_slo(10, 9, "NaN")

    def test_invalid_target(self):
        for target in ["0", "1.01", "-0.2", "none"]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                calculate_slo(10, 9, target)


class AdmissionTests(unittest.TestCase):
    def test_normal_two_tenants(self):
        gate = AdmissionController(2, 1)
        self.assertTrue(gate.admit("a", "tenant-a"))
        self.assertTrue(gate.admit("b", "tenant-b"))
        self.assertEqual(len(gate.active), 2)

    def test_tenant_limit(self):
        gate = AdmissionController(3, 1)
        self.assertTrue(gate.admit("a", "tenant-a"))
        self.assertFalse(gate.admit("b", "tenant-a"))

    def test_global_capacity(self):
        gate = AdmissionController(1, 1)
        self.assertTrue(gate.admit("a", "tenant-a"))
        self.assertFalse(gate.admit("b", "tenant-b"))

    def test_duplicate_identifier(self):
        gate = AdmissionController(2, 2)
        self.assertTrue(gate.admit("a", "tenant-a"))
        self.assertFalse(gate.admit("a", "tenant-b"))
        self.assertEqual(gate.active["a"], "tenant-a")

    def test_release_and_reuse(self):
        gate = AdmissionController(1, 1)
        gate.admit("a", "tenant-a")
        gate.release("a")
        self.assertTrue(gate.admit("b", "tenant-b"))

    def test_double_release(self):
        gate = AdmissionController(1, 1)
        gate.admit("a", "tenant-a")
        gate.release("a")
        with self.assertRaises(KeyError): gate.release("a")

    def test_zero_capacity(self):
        self.assertFalse(AdmissionController(0, 0).admit("a", "tenant-a"))

    def test_negative_capacity(self):
        with self.assertRaises(ValueError): AdmissionController(-1, 1)

    def test_blank_identifier(self):
        with self.assertRaises(ValueError): AdmissionController(1, 1).admit("", "tenant-a")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)

    def test_within_rpo(self):
        result = assess_recovery_point(self.now, self.now-timedelta(minutes=5),
                                       timedelta(minutes=10), True)
        self.assertTrue(result.acceptable)
        self.assertEqual(result.data_age_seconds, 300)

    def test_rpo_exceeded(self):
        self.assertEqual(assess_recovery_point(self.now, self.now-timedelta(minutes=15),
                                               timedelta(minutes=10), True).reason, "rpo_exceeded")

    def test_unverified_integrity(self):
        self.assertEqual(assess_recovery_point(self.now, self.now-timedelta(minutes=1),
                                               timedelta(minutes=10), False).reason, "unverified_integrity")

    def test_future_snapshot(self):
        self.assertEqual(assess_recovery_point(self.now, self.now+timedelta(seconds=1),
                                               timedelta(minutes=10), True).reason, "future_snapshot")

    def test_tz_required(self):
        with self.assertRaises(ValueError):
            assess_recovery_point(self.now.replace(tzinfo=None), self.now, timedelta(minutes=1), True)

    def test_positive_rpo(self):
        with self.assertRaises(ValueError):
            assess_recovery_point(self.now, self.now, timedelta(0), True)

    def test_boundary_rpo(self):
        result = assess_recovery_point(self.now, self.now-timedelta(minutes=10),
                                       timedelta(minutes=10), True)
        self.assertTrue(result.acceptable)


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.required = {"hash", "license", "authorization", "performance"}
        self.critical = {"hash", "authorization"}

    def test_all_pass(self):
        result = evaluate_gate({key: "pass" for key in self.required}, self.required, self.critical)
        self.assertTrue(result.approved)

    def test_missing_evidence(self):
        result = evaluate_gate({"hash": "pass"}, self.required, self.critical)
        self.assertFalse(result.approved)
        self.assertIn("performance", result.blocked)

    def test_critical_waiver_not_allowed(self):
        states = {key: "pass" for key in self.required}
        states["authorization"] = "waived"
        result = evaluate_gate(states, self.required, self.critical)
        self.assertFalse(result.approved)

    def test_noncritical_waiver_visible(self):
        states = {key: "pass" for key in self.required}
        states["performance"] = "waived"
        result = evaluate_gate(states, self.required, self.critical)
        self.assertFalse(result.approved)
        self.assertIn("performance", result.waived)

    def test_failed_control(self):
        states = {key: "pass" for key in self.required}
        states["license"] = "fail"
        self.assertFalse(evaluate_gate(states, self.required, self.critical).approved)

    def test_unrecognized_status(self):
        with self.assertRaises(ValueError):
            evaluate_gate({"hash": "maybe"}, {"hash"})

    def test_no_required_controls(self):
        with self.assertRaises(ValueError): evaluate_gate({}, [])

    def test_unknown_critical_control(self):
        with self.assertRaises(ValueError): evaluate_gate({}, {"hash"}, {"other"})


class ManifestTests(unittest.TestCase):
    def test_hash_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "data.txt").write_text("alpha", encoding="utf-8")
            manifest = build_manifest(directory)
            self.assertTrue(verify_manifest(directory, manifest))
            self.assertEqual(manifest["algorithm"], "sha256")

    def test_tampered_data_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "data.txt"
            path.write_text("alpha", encoding="utf-8")
            manifest = build_manifest(directory)
            path.write_text("beta", encoding="utf-8")
            self.assertFalse(verify_manifest(directory, manifest))

    def test_missing_data_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "data.txt"
            path.write_text("alpha", encoding="utf-8")
            manifest = build_manifest(directory)
            path.unlink()
            self.assertFalse(verify_manifest(directory, manifest))

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(verify_manifest(Path(tmp), {"algorithm": "sha256",
                 "files": {"../secret.txt": {"bytes": 4, "sha256": "bad"}}}))

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "data.txt").write_text("ok", encoding="utf-8")
            (directory / "link.txt").symlink_to(directory / "data.txt")
            with self.assertRaises(ValueError): build_manifest(directory)

    def test_nested_files_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "data").mkdir()
            (directory / "data" / "file.txt").write_text("ok", encoding="utf-8")
            self.assertIn("data/file.txt", build_manifest(directory)["files"])

    def test_manifest_is_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn('"algorithm": "sha256"', manifest_json(Path(tmp)))

    def test_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(verify_manifest(Path(tmp), {"algorithm": "md5", "files": {}}))


if __name__ == "__main__":
    unittest.main()
