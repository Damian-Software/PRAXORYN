"""Offline protocol and safety tests; no production endpoint required."""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client import APIError, LocalChatClient, read_key
from bench import percentile_nearest_rank, run
from audit_policy import make_event, encode_event
from firewall_review import PolicyReject, review_proposal


class MockHandler(BaseHTTPRequestHandler):
    expected_key = "test-key"
    status = 200
    response_mode = "normal"
    calls = 0
    seen_model = None

    def do_POST(self):
        MockHandler.calls += 1
        if self.path != "/v1/chat/completions":
            self.send_response(404); self.end_headers(); return
        if self.headers.get("Authorization") != "Bearer " + self.expected_key:
            self.send_response(401); self.end_headers(); return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        MockHandler.seen_model = body.get("model")
        if self.status != 200:
            self.send_response(self.status); self.end_headers(); return
        if self.response_mode == "malformed":
            out = b'{"choices":[]}'
        elif self.response_mode == "oversized":
            out = b'A' * 2_000_001
        elif self.response_mode == "null":
            out = b'{"choices":[{"message":{"content":null}}]}'
        else:
            out = json.dumps({"choices": [{"message": {"content": "ready"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        try: self.wfile.write(out)
        except (BrokenPipeError, ConnectionResetError): pass

    def log_message(self, *args):
        pass


class HttpClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
        cls.worker = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.worker.start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close(); cls.worker.join(timeout=2)

    def setUp(self):
        MockHandler.status = 200; MockHandler.response_mode = "normal"
        MockHandler.calls = 0; MockHandler.seen_model = None
        self.client = LocalChatClient(self.url, "test-key", timeout=2)

    def test_completion(self):
        self.assertEqual(self.client.chat("hello"), "ready")

    def test_model_propagates(self):
        self.client.chat("hello", "my-generic-model")
        self.assertEqual(MockHandler.seen_model, "my-generic-model")

    def test_missing_auth(self):
        with self.assertRaisesRegex(APIError, "HTTP 401"):
            LocalChatClient(self.url, "wrong", timeout=2).chat("hello")

    def test_server_error_does_not_echo_body(self):
        MockHandler.status = 503
        with self.assertRaisesRegex(APIError, "HTTP 503"):
            self.client.chat("hello")

    def test_invalid_schema(self):
        MockHandler.response_mode = "malformed"
        with self.assertRaisesRegex(APIError, "schema"):
            self.client.chat("hello")

    def test_null_content(self):
        MockHandler.response_mode = "null"
        with self.assertRaises(APIError): self.client.chat("hello")

    def test_oversize(self):
        MockHandler.response_mode = "oversized"
        with self.assertRaisesRegex(APIError, "too large"):
            self.client.chat("hello")

    def test_reject_empty_prompt_before_network(self):
        with self.assertRaises(APIError): self.client.chat("")
        self.assertEqual(MockHandler.calls, 0)

    def test_reject_long_prompt(self):
        with self.assertRaises(APIError): self.client.chat("X" * 8001)

    def test_reject_excessive_tokens(self):
        with self.assertRaises(APIError): self.client.chat("hello", max_tokens=4096)

    def test_reject_unencrypted_remote(self):
        with self.assertRaises(APIError): LocalChatClient("http://example.com:80", "key")

    def test_benchmark_has_real_samples(self):
        metrics = run(self.client, "local-chat", 4, 1)
        self.assertEqual(metrics["samples"], 4)
        self.assertEqual(len(metrics["raw_ms"]), 4)
        self.assertGreaterEqual(metrics["p95_ms"], metrics["min_ms"])
        self.assertEqual(MockHandler.calls, 5)


class SafetyTests(unittest.TestCase):
    def test_key_file(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path)/"api_keys.txt"; p.write_text("secret123\n")
            self.assertEqual(read_key(str(p)), "secret123")

    def test_key_file_reject_multiline(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path)/"api_keys.txt"; p.write_text("a\nb")
            with self.assertRaises(APIError): read_key(str(p))

    def test_audit_exact_allowlist(self):
        encoded = encode_event(make_event("request_completed", 200, 12, "req-1"))
        self.assertEqual(set(json.loads(encoded)), {"timestamp", "event", "status", "duration_ms", "request_id"})
        self.assertNotIn("prompt", encoded)

    def test_audit_reject_payload_injection(self):
        event = make_event("request_completed", 200, 2, "a1")
        event["prompt"] = "secret"
        with self.assertRaises(ValueError): encode_event(event)

    def test_audit_reject_unsafe_id(self):
        with self.assertRaises(ValueError): make_event("request_denied", 403, 4, "secret?token=123")

    def test_percentile(self):
        self.assertEqual(percentile_nearest_rank([1,2,3,4,5], .95), 5)
        self.assertEqual(percentile_nearest_rank([1,2,3,4], .5), 2)

    def test_firewall_requires_approval(self):
        decision = review_proposal("9.9.9.9", 90, 4)
        self.assertEqual(decision["decision"], "REVIEW_REQUIRED")
        self.assertFalse(decision["executed"])

    def test_firewall_rejects_network(self):
        with self.assertRaises(PolicyReject): review_proposal("9.9.9.0/24", 90, 4)

    def test_firewall_rejects_private(self):
        with self.assertRaises(PolicyReject): review_proposal("10.0.0.1", 90, 4)

    def test_firewall_rejects_protected(self):
        with self.assertRaises(PolicyReject): review_proposal("1.1.1.1", 90, 4)

    def test_firewall_rejects_long_ttl(self):
        with self.assertRaises(PolicyReject): review_proposal("9.9.9.9", 90000, 4)

    def test_firewall_rejects_weak_evidence(self):
        with self.assertRaises(PolicyReject): review_proposal("9.9.9.9", 90, 1)


# File-level configuration smoke checks. A real Nginx/systemd integration
# test must still be run on the deployment host.
class ConfigurationTests(unittest.TestCase):
    def test_nginx_listens_only_on_loopback(self):
        path = Path(__file__).resolve().parents[1]/'config'/'nginx_localai.conf'
        conf = path.read_text()
        self.assertIn('listen 127.0.0.1:8080;', conf)
        self.assertNotIn('listen 0.0.0.0:', conf)

    def test_nginx_log_excludes_request_content_fields(self):
        path = Path(__file__).resolve().parents[1]/'config'/'nginx_localai.conf'
        conf = path.read_text()
        start = conf.index('log_format localai_min')
        fmt = conf[start:conf.index(';', start)]
        import re
        tokens = set(re.findall(r'\$[a-zA-Z_]+', fmt))
        for field in ('$request_uri', '$request', '$remote_addr', '$http_authorization', '$http_cookie'):
            self.assertNotIn(field, tokens)

    def test_systemd_uses_unprivileged_identity(self):
        path = Path(__file__).resolve().parents[1]/'config'/'localai-llama.service.example'
        unit = path.read_text()
        self.assertIn('User=localai', unit)
        self.assertIn('--host 127.0.0.1', unit)
        self.assertIn('--api-key-file', unit)
        directives = [line.strip() for line in unit.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        self.assertNotIn('PrivateDevices=true', directives)

    def test_php_requires_reverse_proxy_identity(self):
        php = (Path(__file__).resolve().parents[1]/'web'/'index.php').read_text()
        self.assertIn("$_SERVER['REMOTE_USER']", php)
        self.assertIn('hash_equals', php)
        self.assertIn('htmlspecialchars', php)

if __name__ == "__main__":
    unittest.main()
