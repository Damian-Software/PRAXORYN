import unittest

from audit import EVENT_FIELDS, make_event


class AuditTests(unittest.TestCase):
    ID = "00000000-0000-4000-8000-000000000000"

    def test_minimal_fields(self):
        record = make_event(self.ID, "principal-1", "deny", "not_authorized")
        self.assertEqual(set(record), EVENT_FIELDS)
        self.assertNotIn("prompt", record)
        self.assertNotIn("response", record)

    def test_reject_unknown_reason(self):
        with self.assertRaises(ValueError):
            make_event(self.ID, "principal-1", "deny", "full_prompt_dump")

    def test_reject_unknown_decision(self):
        with self.assertRaises(ValueError):
            make_event(self.ID, "principal-1", "execute", "allowed")

    def test_reject_invalid_request_id(self):
        with self.assertRaises(ValueError):
            make_event("invalid-id", "principal-1", "allow", "allowed")

    def test_reject_empty_principal(self):
        with self.assertRaises(ValueError):
            make_event(self.ID, "", "allow", "allowed")


if __name__ == "__main__":
    unittest.main()
