import unittest
from pathlib import Path
import tempfile,hashlib,json
from praxoryn_mediaops.verify import verify_manifest
from praxoryn_mediaops.batch import run_batch

class ManifestTests(unittest.TestCase):
    def test_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'x.txt').write_text('abc')
            m={'artifacts':[{'file':'x.txt','bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()}]}
            (p/'manifest.json').write_text(json.dumps(m))
            self.assertEqual(verify_manifest(p),[])
    def test_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'x.txt').write_text('abc')
            m={'artifacts':[{'file':'x.txt','bytes':3,'sha256':'0'*64}]}
            (p/'manifest.json').write_text(json.dumps(m))
            self.assertIn('wrong digest: x.txt',verify_manifest(p))
    def test_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'manifest.json').write_text(json.dumps({'artifacts':[{'file':'../secret','bytes':1,'sha256':'a'}]}))
            self.assertIn('unsafe file name',verify_manifest(p))
    def test_limit(self):
        with self.assertRaises(ValueError): run_batch(Path('/tmp'),Path('/tmp'),max_jobs=0)
