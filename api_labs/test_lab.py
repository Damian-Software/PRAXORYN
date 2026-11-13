"""GPU-free unit tests. All HTTP calls are mocked by a local fixture."""
import io
import json
import unittest
from unittest.mock import patch, Mock

import api_client
import safe_tools


class ToolsTests(unittest.TestCase):
    def test_deny_unlisted_commands_without_invocation(self):
        with patch("safe_tools.subprocess.run") as call:
            denied = safe_tools.run_diagnostic("rm -rf /")
        self.assertEqual(denied["status"], 403)
        call.assert_not_called()

    def test_allowlisted_command_is_not_shell(self):
        with patch("safe_tools.subprocess.run", return_value=Mock(returncode=0, stdout="ok")) as call:
            result = safe_tools.run_diagnostic("kernel")
        self.assertTrue(result["ok"])
        argv = call.call_args.args[0]
        self.assertEqual(argv, ["/usr/bin/uname", "-r"])
        self.assertFalse(call.call_args.kwargs["shell"])
        self.assertEqual(call.call_args.kwargs["timeout"], 3)

    def test_output_truncation(self):
        with patch("safe_tools.subprocess.run", return_value=Mock(returncode=0, stdout="x" * 5000)):
            result = safe_tools.run_diagnostic("disk")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["output"]), 4096)


class APITests(unittest.TestCase):
    def test_reject_arbitrary_provider(self):
        with self.assertRaises(ValueError):
            api_client.request_json("attacker", "/v1/models")

    def test_reject_bad_routes(self):
        for route in ("//example.com", "/../etc/passwd", "http://bad", "/v1/models?q=secret"):
            with self.assertRaises(ValueError):
                api_client.request_json("llama", route)

    def test_llama_models(self):
        with patch("api_client.request_json", return_value={"data": [{"id": "test-gguf"}]}) as request:
            self.assertEqual(api_client.model_ids("llama"), ["test-gguf"])
        self.assertEqual(request.call_args.args, ("llama", "/v1/models"))

    def test_ollama_models(self):
        with patch("api_client.request_json", return_value={"models": [{"name": "local-model"}]}) as request:
            self.assertEqual(api_client.model_ids("ollama"), ["local-model"])
        self.assertEqual(request.call_args.args, ("ollama", "/api/tags"))

    def test_chat_llama(self):
        with patch("api_client.request_json", return_value={"choices": [{"message": {"content": "done"}}]}) as req:
            self.assertEqual(api_client.chat("llama", "m", "test"), "done")
        self.assertEqual(req.call_args.args[1], "/v1/chat/completions")
        self.assertFalse(req.call_args.args[2]["stream"])

    def test_chat_ollama(self):
        with patch("api_client.request_json", return_value={"message": {"content": "done"}}) as req:
            self.assertEqual(api_client.chat("ollama", "m", "test"), "done")
        self.assertEqual(req.call_args.args[1], "/api/chat")

    def test_reject_oversized_prompt(self):
        with self.assertRaises(ValueError):
            api_client.chat("llama", "model", "x" * 9000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
