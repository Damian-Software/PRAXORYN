import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from praxops.client import safe_base, chat, models, health
from praxops.diagnostics import gate, report
from praxops.metadata import append, retain


def event(dt, status='ok', latency=100):
    return {'timestamp':dt.isoformat(),'operation':'synthetic_probe','status':status,'latency_ms':latency,'model_tag':'mock-model'}


class ToolTests(unittest.TestCase):
    def test_loopback(self):
        self.assertEqual(safe_base('http://127.0.0.1:8080'),'http://127.0.0.1:8080')
        for url in ['https://example.com', 'http://example.com', 'http://127.0.0.1:80/secret', 'http://a:b@localhost:8765']:
            with self.assertRaises(ValueError): safe_base(url)

    def test_metadata_policy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'private/log.jsonl'; row=event(datetime.now(timezone.utc))
            append(p,row)
            self.assertEqual(len(report(p)['statuses']),1)
            with self.assertRaises(ValueError): append(p,{**row,'prompt':'private'})

    def test_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.jsonl'
            for n in range(6):append(p,event(datetime.now(timezone.utc),latency=100+n))
            self.assertEqual(report(p)['requests'],6)
            self.assertTrue(gate(p,5,.1,150)[0])
            self.assertFalse(gate(p,7,.1,150)[0])
            append(p,event(datetime.now(timezone.utc),'unavailable',0))
            self.assertFalse(gate(p,5,.1,150)[0])

    def test_retention(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.jsonl';now=datetime.now(timezone.utc)
            append(p,event(now-timedelta(days=50)))
            append(p,event(now))
            self.assertEqual(retain(p,14,now),(2,1))

if __name__ == '__main__':unittest.main()
