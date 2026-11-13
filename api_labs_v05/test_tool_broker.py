import unittest

from tool_broker import DeniedAction, Principal, execute_proposal


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.viewer = Principal("principal-1", frozenset({"get_service_status"}))

    def test_allowed_read(self):
        result = execute_proposal(self.viewer, "get_service_status", {"service": "model"})
        self.assertEqual(result["status"], "not_connected")

    def test_deny_shell(self):
        with self.assertRaises(DeniedAction):
            execute_proposal(self.viewer, "run_shell", {"command": "date"})

    def test_unknown_service(self):
        with self.assertRaises(DeniedAction):
            execute_proposal(self.viewer, "get_service_status", {"service": "root"})

    def test_extra_parameter(self):
        with self.assertRaises(DeniedAction):
            execute_proposal(self.viewer, "get_service_status", {"service": "model", "cmd": "id"})

    def test_no_capability(self):
        with self.assertRaises(DeniedAction):
            execute_proposal(self.viewer, "list_model_aliases", {})

    def test_authorized_aliases(self):
        principal = Principal("principal-2", frozenset({"list_model_aliases"}))
        result = execute_proposal(principal, "list_model_aliases", {})
        self.assertIn("assistant-default", result["aliases"])

    def test_non_mapping_parameters(self):
        with self.assertRaises(DeniedAction):
            execute_proposal(self.viewer, "get_service_status", "model")

    def test_missing_principal_id(self):
        principal = Principal("", frozenset({"get_service_status"}))
        with self.assertRaises(DeniedAction):
            execute_proposal(principal, "get_service_status", {"service": "model"})

    def test_denied_write_proposal(self):
        with self.assertRaises(DeniedAction):
            execute_proposal(self.viewer, "send_email", {"to": "someone@example.org"})


if __name__ == "__main__":
    unittest.main()
