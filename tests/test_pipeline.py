import unittest
import tempfile
import json
from pathlib import Path
from praxoryn_mediaops.pipeline import publish
from praxoryn_mediaops.media import preview_image

class PipelineTests(unittest.TestCase):
    def test_preview(self):
        with tempfile.TemporaryDirectory() as temp:
            p=preview_image(Path(temp)/'image.png','abc')
            self.assertEqual(p.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
    def test_full_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            brief=root/'brief.json'
            brief.write_text(json.dumps({'title':'Sample-01','prompt':'Example','kind':'internal'}))
            dest=publish(brief,root/'out')
            self.assertTrue((dest/'report.docx').is_file())
            self.assertTrue((dest/'report.pdf').is_file())
            self.assertTrue((dest/'still-preview.mp4').is_file())
            self.assertTrue((dest/'manifest.json').is_file())
            self.assertIn('OFFLINE DEMO ONLY',(dest/'draft.txt').read_text())
            with self.assertRaises(FileExistsError): publish(brief,root/'out')
