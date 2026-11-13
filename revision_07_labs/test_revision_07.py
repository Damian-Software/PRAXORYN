import unittest
from provider_registry import Provider, CATALOG
from gpu_admission import AdmissionPlanner, JobEstimate
from job_state import JobMachine
from audit_policy import audit_event, pseudonymize

KEY = b"local-ai-audit-demo-key-do-not-use-in-production-2026"

class RegistryTests(unittest.TestCase):
    def test_known_route(self):
        self.assertEqual(CATALOG["ollama_native"].url_for("chat"), "http://127.0.0.1:11434/api/chat")
    def test_undeclared_capability(self):
        with self.assertRaises(ValueError): CATALOG["llama_cpp"].url_for("video")
    def test_remote_disallowed(self):
        with self.assertRaises(ValueError): Provider("bad", "https://example.org:443", {"chat": "/api/chat"})
    def test_credentials_disallowed(self):
        with self.assertRaises(ValueError): Provider("bad", "http://u:p@localhost:8080", {"chat": "/api/chat"})
    def test_invalid_path(self):
        with self.assertRaises(ValueError): Provider("bad", "http://localhost:1234", {"chat": "//other"})
    def test_invalid_operation(self):
        with self.assertRaises(ValueError): Provider("bad", "http://localhost:1234", {"shell": "/run"})

class MemoryTests(unittest.TestCase):
    def test_overcommit_rejected(self):
        planner = AdmissionPlanner(16, 3)
        self.assertTrue(planner.admit(JobEstimate("text", 6, 1, 1)))
        self.assertFalse(planner.admit(JobEstimate("video", 7, 3, 2)))
        self.assertEqual(planner.free_estimate_gib, 5)
    def test_release(self):
        planner = AdmissionPlanner(16, 3)
        planner.admit(JobEstimate("a", 4, 1, 1))
        planner.release("a")
        self.assertEqual(planner.free_estimate_gib, 13)
    def test_invalid_reserve(self):
        with self.assertRaises(ValueError): AdmissionPlanner(16, 16)
    def test_negative_memory(self):
        with self.assertRaises(ValueError): JobEstimate("x", -1, 0, 0).estimated_gib
    def test_duplicate_job(self):
        planner = AdmissionPlanner(16, 3)
        planner.admit(JobEstimate("a", 1, 1, 1))
        with self.assertRaises(ValueError): planner.admit(JobEstimate("a", 1, 1, 1))

class JobTests(unittest.TestCase):
    def test_idempotent_submit(self):
        machine = JobMachine()
        a = machine.submit("tenant-a", "j1", "key")
        b = machine.submit("tenant-a", "j2", "key")
        self.assertIs(a, b)
    def test_tenant_separation(self):
        machine = JobMachine()
        a = machine.submit("tenant-a", "j1", "key")
        b = machine.submit("tenant-b", "j1", "key")
        self.assertIsNot(a, b)
    def test_valid_success(self):
        machine = JobMachine()
        job = machine.submit("t", "j", "k")
        machine.transition(job, "running")
        machine.transition(job, "succeeded")
        self.assertEqual(job.attempts, 1)
    def test_invalid_skip(self):
        machine = JobMachine()
        job = machine.submit("t", "j", "k")
        with self.assertRaises(ValueError): machine.transition(job, "succeeded")
    def test_no_retry_after_three_attempts(self):
        machine = JobMachine()
        job = machine.submit("t", "j", "k")
        for _ in range(3):
            machine.transition(job, "running")
            machine.transition(job, "failed")
            if job.attempts < 3: machine.transition(job, "queued")
        with self.assertRaises(ValueError): machine.transition(job, "queued")

class AuditTests(unittest.TestCase):
    def test_pseudonymization_is_stable(self):
        self.assertEqual(pseudonymize("alice", KEY), pseudonymize("alice", KEY))
    def test_different_user(self):
        self.assertNotEqual(pseudonymize("alice", KEY), pseudonymize("bob", KEY))
    def test_sensitive_fields_dropped(self):
        event = audit_event({"request_id":"r1", "tenant_id":"t", "action":"chat", "outcome":"succeeded", "prompt":"private", "api_key":"secret", "ip":"192.0.2.1", "duration_ms":11}, "alice", KEY)
        self.assertNotIn("prompt", event)
        self.assertNotIn("api_key", event)
        self.assertNotIn("ip", event)
        self.assertEqual(event["duration_ms"], 11)
    def test_no_bad_action(self):
        with self.assertRaises(ValueError): audit_event({"request_id":"r", "tenant_id":"t", "action":"shutdown", "outcome":"accepted"}, "a", KEY)
    def test_short_key(self):
        with self.assertRaises(ValueError): pseudonymize("a", b"short")
    def test_duration_bool_is_rejected(self):
        with self.assertRaises(ValueError): audit_event({"request_id":"r", "tenant_id":"t", "action":"chat", "outcome":"accepted", "duration_ms":True}, "a", KEY)

if __name__ == "__main__": unittest.main()
