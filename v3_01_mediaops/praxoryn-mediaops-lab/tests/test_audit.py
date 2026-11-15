import unittest
import tempfile
from pathlib import Path
from praxoryn_mediaops.audit import log_event,show_events

class AuditTests(unittest.TestCase):
    def test_log(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'log.sqlite'
            log_event(path,'demo','ok',4)
            rows=show_events(path)
            self.assertEqual(rows[0]['artifact_count'],4)
            self.assertNotIn('prompt',str(rows))
    def test_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(show_events(Path(temp)/'none.sqlite'),[])
    def test_invalid_status(self):
        with self.assertRaises(ValueError):
            log_event(Path('/tmp/unused.sqlite'),'demo','secret')
