import io
import json
import sys
import unittest
from unittest.mock import patch, MagicMock

import bench_client

class BenchClientTests(unittest.TestCase):
    def test_successful_response_parsing(self):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch("bench_client.urllib.request.urlopen", return_value=response):
            with patch("bench_client.json.load", return_value={
                "model": "test-model", "usage": {"completion_tokens": 12}
            }):
                value = bench_client.run_once(
                    "http://127.0.0.1:8080", "test-model", 32)
        self.assertEqual(value["status"], 200)
        self.assertEqual(value["model"], "test-model")
        self.assertEqual(value["completion_tokens"], 12)
        self.assertGreaterEqual(value["elapsed_ms"], 0)

    def test_missing_token_usage_stays_unknown(self):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch("bench_client.urllib.request.urlopen", return_value=response):
            with patch("bench_client.json.load", return_value={}):
                value = bench_client.run_once(
                    "http://127.0.0.1:8080", "test-model", 32)
        self.assertIsNone(value["completion_tokens"])

if __name__ == "__main__":
    unittest.main()
