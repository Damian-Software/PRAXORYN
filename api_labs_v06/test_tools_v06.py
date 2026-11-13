"""Offline tests; they do not measure GPU inference."""
from __future__ import annotations
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib import request

from artifact_manifest_v06 import describe_file
from bench_v06 import endpoint, measure, _valid_count
from image_generate_v06 import validate
from summarize_v06 import nearest_rank, summarize
from vram_budget_v06 import kv_bytes


class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        obj = json.loads(self.rfile.read(length))
        if self.path != '/v1/chat/completions':
            self.send_response(404)
            self.end_headers()
            return
        data = {'choices': [{'message': {'role': 'assistant', 'content': 'READY'}}],
                'usage': {'prompt_tokens': 12, 'completion_tokens': 2}}
        raw = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class TestCalculations(unittest.TestCase):
    def test_one_gib(self):
        self.assertEqual(kv_bytes(32, 8, 128, 8192, 2, 1), 1024 ** 3)

    def test_two_sequences(self):
        self.assertEqual(kv_bytes(32, 8, 128, 8192, 2, 2), 2 * 1024 ** 3)

    def test_reject_zero(self):
        with self.assertRaises(ValueError):
            kv_bytes(32, 8, 128, 0, 2, 1)

    def test_reject_boolean(self):
        with self.assertRaises(ValueError):
            kv_bytes(True, 8, 128, 100, 2, 1)

    def test_nearest_rank(self):
        self.assertEqual(nearest_rank([10, 30, 20, 40, 50], 95), 50)

    def test_empty_percentile(self):
        self.assertIsNone(nearest_rank([], 95))

    def test_percentile_bad_value(self):
        with self.assertRaises(ValueError):
            nearest_rank([3], 0)

    def test_summary(self):
        s = summarize([{'ok': True, 'latency_ms': 10}, {'ok': False, 'latency_ms': 1}])
        self.assertEqual(s['successes'], 1)
        self.assertEqual(s['success_rate'], 0.5)
        self.assertIsNone(s['mean_e2e_tokens_per_second'])

    def test_empty_summary(self):
        self.assertIsNone(summarize([])['success_rate'])


class TestEndpoint(unittest.TestCase):
    def test_localhost(self):
        self.assertEqual(endpoint('http://127.0.0.1:8080/v1'),
                         'http://127.0.0.1:8080/v1/chat/completions')

    def test_remote_http_rejected_even_if_allowed(self):
        with self.assertRaises(ValueError):
            endpoint('http://example.com/v1', allow_remote=True)

    def test_remote_requires_opt_in(self):
        with self.assertRaises(ValueError):
            endpoint('https://example.com/v1')

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            endpoint('http://me:secret@localhost:8080/v1')

    def test_unknown_api_path_rejected(self):
        with self.assertRaises(ValueError):
            endpoint('http://localhost:8080/private')

    def test_usage_type_validation(self):
        self.assertIsNone(_valid_count(True))
        self.assertIsNone(_valid_count(-1))
        self.assertEqual(_valid_count(5), 5)


class TestArtifacts(unittest.TestCase):
    def test_regular_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'demo.bin'
            p.write_bytes(b'abc')
            out = describe_file(p)
            self.assertEqual(out['size_bytes'], 3)
            self.assertEqual(out['sha256'], hashlib.sha256(b'abc').hexdigest())

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'file.bin'
            p.write_bytes(b'data')
            link = Path(directory) / 'alias.bin'
            link.symlink_to(p)
            with self.assertRaises(ValueError):
                describe_file(link)

    def test_image_limits(self):
        validate(768, 768, 20)
        with self.assertRaises(ValueError):
            validate(770, 768, 20)
        with self.assertRaises(ValueError):
            validate(768, 768, 0)


class TestMockAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), MockHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)
        cls.server.server_close()

    def test_mock_reply(self):
        url = endpoint(f'http://127.0.0.1:{self.server.server_port}/v1')
        result = measure(url, 'fixture-model')
        self.assertTrue(result['ok'])
        self.assertEqual(result['completion_tokens'], 2)
        self.assertNotIn('content', result)

    def test_not_found_does_not_expose_response_body(self):
        url = f'http://127.0.0.1:{self.server.server_port}/v1/missing'
        result = measure(url, 'fixture-model')
        self.assertFalse(result['ok'])
        self.assertEqual(result['status_code'], 404)
        self.assertEqual(result['error_class'], 'HTTPError')
        self.assertNotIn('body', result)


if __name__ == '__main__':
    unittest.main()
