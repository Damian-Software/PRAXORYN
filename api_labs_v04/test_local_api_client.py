"""Offline contract tests. Starts a loopback HTTP mock, not a model."""
from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from local_api_client import ApiClientError, ApiProfile, chat, list_models
from sse_events import is_stream_done, iter_sse_events


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self.respond(200, {"data": [{"id": "mock-llm"}]})
        elif self.path == "/api/tags":
            self.respond(200, {"models": [{"name": "mock-ollama"}]})
        else:
            self.respond(404, {"error": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length))
        if data.get("model") == "offline-error":
            self.respond(503, {"error": "temporarily_unavailable"})
        elif self.path == "/v1/chat/completions":
            self.respond(200, {"choices": [{"message": {"content": "OpenAI mock"}}]})
        elif self.path == "/api/chat":
            self.respond(200, {"message": {"content": "Ollama mock"}, "done": True})
        else:
            self.respond(404, {"error": "not_found"})

    def respond(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format: str, *args: object) -> None:
        pass  # The mock intentionally avoids request body logging.


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def openai_profile(self, model="mock-llm") -> ApiProfile:
        return ApiProfile("openai", f"http://127.0.0.1:{self.port}/v1", model)

    def ollama_profile(self) -> ApiProfile:
        return ApiProfile("ollama", f"http://127.0.0.1:{self.port}/api", "mock-ollama")

    def test_openai_catalogue(self) -> None:
        self.assertEqual(list_models(self.openai_profile()), ["mock-llm"])

    def test_ollama_catalogue(self) -> None:
        self.assertEqual(list_models(self.ollama_profile()), ["mock-ollama"])

    def test_openai_chat(self) -> None:
        self.assertEqual(chat(self.openai_profile(), "Test input"), "OpenAI mock")

    def test_ollama_chat(self) -> None:
        self.assertEqual(chat(self.ollama_profile(), "Test input"), "Ollama mock")

    def test_http_error_is_sanitized(self) -> None:
        with self.assertRaisesRegex(ApiClientError, "HTTP 503"):
            chat(self.openai_profile("offline-error"), "Very private prompt")

    def test_remote_host_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ApiProfile("openai", "http://example.com/v1", "test")

    def test_embedded_password_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ApiProfile("openai", "http://user:secret@127.0.0.1:8080/v1", "test")

    def test_invalid_api_path_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ApiProfile("openai", "http://127.0.0.1:8080/api", "test")

    def test_sse_multiline_payload(self) -> None:
        events = list(iter_sse_events(["event: update\n", "data: one\n", "data: two\n", "\n"]))
        self.assertEqual(events[0], {"event": "update", "id": "", "data": "one\ntwo"})

    def test_sse_comment_and_done(self) -> None:
        events = list(iter_sse_events([": heartbeat\n", "data: [DONE]\n", "\n"]))
        self.assertEqual(len(events), 1)
        self.assertTrue(is_stream_done(events[0]))

    def test_sse_split_transport_is_not_assumed(self) -> None:
        events = list(iter_sse_events(["data: {\"x\":1}\n", "\n", "data: [DONE]\n", "\n"]))
        self.assertEqual(len(events), 2)
        self.assertFalse(is_stream_done(events[0]))

    def test_unauthorized_schema_not_silently_accepted(self) -> None:
        with self.assertRaises(ValueError):
            ApiProfile("other", f"http://127.0.0.1:{self.port}/v1", "test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
