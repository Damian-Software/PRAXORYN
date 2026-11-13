import unittest
from praxoryn_mediaops.comfy import prepare, _local
from praxoryn_mediaops.llm import chat

class APITests(unittest.TestCase):
    def test_comfy_prepare(self):
        src={'6': {'inputs': {'text':'old'}, 'class_type':'CLIPTextEncode'}}
        x=prepare(src,'6','text','new')
        self.assertEqual(x['6']['inputs']['text'],'new')
        self.assertEqual(src['6']['inputs']['text'],'old')
    def test_bad_node(self):
        with self.assertRaises(ValueError): prepare({},'6','text','a')
    def test_bad_field(self):
        with self.assertRaises(ValueError): prepare({'6':{'inputs':{'foo':1}}},'6','foo','a')
    def test_loopback(self): self.assertEqual(_local('http://127.0.0.1:8188'),'http://127.0.0.1:8188')
    def test_remote_denied(self):
        with self.assertRaises(ValueError): _local('http://example.com')
    def test_remote_llm_denied(self):
        with self.assertRaises(ValueError): chat('abc',base_url='https://public.example',model='x')
