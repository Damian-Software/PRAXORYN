from __future__ import annotations
import os
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1] / 'app'))
from rag_core import (RagStore, RagConfig, InputError, UpstreamError, answer,
                      safe_source_path, require_loopback_upstream, read_secret,
                      split_chunks, search_expression)
from rag_api import create_app


class RagLabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.docs = self.base / 'docs'
        self.docs.mkdir()
        (self.docs / 'incident.md').write_text(
            'The incident owner records event identifiers, timestamps and approval. '
            'Rollback plans are mandatory. ' * 20, encoding='utf-8')
        self.db = self.base / 'rag.db'
        self.store = RagStore(self.db)
        self.addCleanup(self.store.close)
        self.app_key_file = self.base / 'app.token'
        self.app_key_file.write_text('app_test_secure_token_1234567890', encoding='utf-8')
        self.app_key_file.chmod(0o600)
        self.up_key_file = self.base / 'upstream.token'
        self.up_key_file.write_text('upstream_test_token_1234567890', encoding='utf-8')
        self.up_key_file.chmod(0o600)
        self.config = RagConfig(self.db, self.docs, 'local-model',
                                'http://127.0.0.1:8080',
                                self.up_key_file, self.app_key_file)

    def test_01_initial_database(self):
        self.assertEqual(self.store.stats(), {'documents':0,'chunks':0})

    def test_02_index_document(self):
        result = self.store.ingest(self.docs, 'incident.md')
        self.assertEqual(result['status'], 'indexed')
        self.assertGreater(result['chunks'], 1)

    def test_03_index_idempotency(self):
        self.store.ingest(self.docs, 'incident.md')
        self.assertEqual(self.store.ingest(self.docs, 'incident.md')['status'], 'unchanged')
        self.assertEqual(self.store.stats()['documents'], 1)

    def test_04_search_hit(self):
        self.store.ingest(self.docs, 'incident.md')
        hits = self.store.search('incident owner')
        self.assertTrue(hits)
        self.assertEqual(hits[0]['label'], 'S1')

    def test_05_search_no_hit(self):
        self.store.ingest(self.docs, 'incident.md')
        self.assertEqual(self.store.search('unicorn satellite'), [])

    def test_06_search_syntax_is_escaped(self):
        self.assertEqual(search_expression('incident OR rollback'),
                         '"incident" AND "or" AND "rollback"')
        self.store.ingest(self.docs, 'incident.md')
        self.assertIsInstance(self.store.search('incident OR rollback'), list)

    def test_07_reject_absolute_path(self):
        with self.assertRaises(InputError):
            safe_source_path(self.docs, '/etc/passwd')

    def test_08_reject_escape(self):
        (self.base / 'escape.md').write_text('secret')
        with self.assertRaises(InputError):
            safe_source_path(self.docs, '../escape.md')

    def test_09_reject_symlink(self):
        (self.docs / 'link.md').symlink_to('incident.md')
        with self.assertRaises(InputError):
            safe_source_path(self.docs, 'link.md')

    def test_10_reject_disallowed_extension(self):
        (self.docs / 'bad.html').write_text('data')
        with self.assertRaises(InputError):
            safe_source_path(self.docs, 'bad.html')

    def test_11_reject_binary_document(self):
        (self.docs / 'bad.txt').write_bytes(b'\xff\xfe')
        with self.assertRaises(InputError):
            self.store.ingest(self.docs, 'bad.txt')

    def test_12_reindex_modified_document(self):
        self.store.ingest(self.docs, 'incident.md')
        (self.docs / 'incident.md').write_text('New zeppelin policy.', encoding='utf-8')
        self.assertEqual(self.store.ingest(self.docs,'incident.md')['status'], 'indexed')
        self.assertEqual(self.store.search('incident owner'),[])
        self.assertTrue(self.store.search('zeppelin'))

    def test_13_remove_deletes_from_fts(self):
        self.store.ingest(self.docs, 'incident.md')
        self.assertEqual(self.store.remove('incident.md'), 1)
        self.assertEqual(self.store.search('incident owner'), [])
        self.assertEqual(self.store.stats()['chunks'],0)

    def test_14_no_document_refuses_model_call(self):
        def unexpected(*args):
            self.fail('Should not invoke model without evidence')
        self.assertEqual(answer(self.store, 'incident owner', self.config, unexpected)['status'],
                         'no_evidence')

    def test_15_answer_with_citation(self):
        self.store.ingest(self.docs,'incident.md')
        fake = lambda cfg, question, hits: 'The owner records approvals [S1].'
        result = answer(self.store,'incident owner',self.config,fake)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['sources'][0]['source'],'incident.md')

    def test_16_uncited_answer_needs_review(self):
        self.store.ingest(self.docs,'incident.md')
        fake = lambda cfg, question, hits: 'Unverified text.'
        result = answer(self.store,'incident owner',self.config,fake)
        self.assertEqual(result['status'],'needs_review')
        self.assertIsNone(result['answer'])

    def test_17_unknown_citation_needs_review(self):
        self.store.ingest(self.docs,'incident.md')
        fake = lambda cfg, question, hits: 'Wrong reference [S999].'
        self.assertEqual(answer(self.store,'incident owner',self.config,fake)['status'],
                         'needs_review')

    def test_18_loopback_accepted(self):
        self.assertEqual(require_loopback_upstream('http://127.0.0.1:8080'),
                         'http://127.0.0.1:8080')

    def test_19_remote_upstream_rejected(self):
        with self.assertRaises(InputError):
            require_loopback_upstream('http://8.8.8.8:8000')

    def test_20_secret_permissions(self):
        self.app_key_file.chmod(0o644)
        with self.assertRaises(InputError):
            read_secret(self.app_key_file)

    def test_21_fresh_db_private(self):
        self.assertEqual(self.db.stat().st_mode & 0o777,0o600)

    def test_22_api_rejects_anonymous(self):
        with TestClient(create_app(self.config, generate=lambda *_:'ok [S1]')) as client:
            self.assertEqual(client.post('/v1/rag/answers',json={'question':'incident owner'}).status_code,401)

    def test_23_api_rejects_extra_fields(self):
        with TestClient(create_app(self.config, generate=lambda *_:'ok [S1]')) as client:
            response = client.post('/v1/rag/answers',headers=self.headers(),
                                   json={'question':'incident owner','tenant_id':'another'})
            self.assertEqual(response.status_code,400)

    def test_24_api_answers_with_source(self):
        self.store.ingest(self.docs,'incident.md')
        with TestClient(create_app(self.config, generate=lambda *_:'Records are required [S1].')) as client:
            response = client.post('/v1/rag/answers',headers=self.headers(),
                                   json={'question':'incident owner'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['status'],'answered')
            self.assertEqual(response.headers['cache-control'],'no-store')

    def test_25_api_blocks_large_request(self):
        with TestClient(create_app(self.config, generate=lambda *_:'ok [S1]')) as client:
            response = client.post('/v1/rag/answers',headers=self.headers(),
                                   content=b'{"question":"' + b'A'*8200 + b'"}')
            self.assertEqual(response.status_code,413)

    def test_26_api_failure_hides_details(self):
        self.store.ingest(self.docs,'incident.md')
        def fail(*_): raise UpstreamError('Internal secret')
        with TestClient(create_app(self.config,generate=fail)) as client:
            response = client.post('/v1/rag/answers',headers=self.headers(),
                                   json={'question':'incident owner'})
            self.assertEqual(response.status_code,503)
            self.assertNotIn('Internal secret',response.text)

    def test_27_api_unauthorized_health_works(self):
        with TestClient(create_app(self.config, generate=lambda *_:'ok [S1]')) as client:
            self.assertEqual(client.get('/healthz').json(),{'status':'ok'})

    def test_28_index_integrity(self):
        self.store.ingest(self.docs,'incident.md')
        self.assertEqual(self.store.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.store.conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")

    def test_29_chunk_ranges(self):
        text = 'lorem ' * 300
        chunks = split_chunks(text)
        self.assertGreater(len(chunks),1)
        self.assertTrue(all(0 <= s < e <= len(text) for s,e,_ in chunks))

    def test_30_question_size_bounded(self):
        with self.assertRaises(InputError):
            self.store.search('x'*1001)

    def headers(self):
        return {'Authorization':'Bearer '+self.app_key_file.read_text(),
                'Content-Type':'application/json'}


if __name__ == '__main__':
    unittest.main()

# Additional evaluation contract checks are declared in a separate class to
# keep the original numbered test sequence stable.
class RetrievalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.joinpath('a.md').write_text('incident owner approval')
        self.store = RagStore(self.root / 'db.sqlite3')
        self.addCleanup(self.store.close)
        self.store.ingest(self.root, 'a.md')

    def test_metrics_with_positive_and_negative(self):
        from rag_eval import evaluate
        result = evaluate(self.store,[
            {'question':'incident owner','expected_source':'a.md'},
            {'question':'unicorn satellite','expected_source':None}],k=4)
        self.assertEqual(result['hit_at_k'],1.0)
        self.assertEqual(result['negative_rejection_rate'],1.0)

    def test_metrics_reject_unsafe_case_shape(self):
        from rag_eval import evaluate
        with self.assertRaises(InputError):
            evaluate(self.store,[{'question':'incident owner','expected_source':'a.md','tenant':'x'}])

    def test_metrics_reject_empty_suite(self):
        from rag_eval import evaluate
        with self.assertRaises(InputError):
            evaluate(self.store,[])

class LocalModelContractTests(unittest.TestCase):
    def setUp(self):
        import http.server
        import threading
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.secret = self.root/'secret.token'
        self.secret.write_text('safe_upstream_secret_1234567890')
        self.secret.chmod(0o600)
        self.app_secret = self.root/'app.token'
        self.app_secret.write_text('safe_app_secret_1234567890')
        self.app_secret.chmod(0o600)
        self.captured = []
        self.status = 200
        self.payload = {'choices':[{'message':{'content':'Approved [S1].'}}]}
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_args):
                pass
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length','0')))
                owner.captured.append((self.path,self.headers.get('Authorization'),json.loads(raw)))
                self.send_response(owner.status)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(json.dumps(owner.payload).encode('utf-8'))
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.config = RagConfig(self.root/'db.sqlite3',self.root,'test-model',
                                f'http://127.0.0.1:{self.server.server_port}',
                                self.secret,self.app_secret)
        self.hits = [{'label':'S1','source':'incident.md','part':1,'text':'approved process'}]

    def test_existing_api_contract(self):
        from rag_core import call_existing_api
        self.assertEqual(call_existing_api(self.config,'Approval?',self.hits), 'Approved [S1].')
        path,authorization,payload = self.captured[0]
        self.assertEqual(path,'/v1/chat/completions')
        self.assertEqual(authorization,'Bearer '+self.secret.read_text())
        self.assertEqual(payload['model'],'test-model')
        self.assertFalse(payload['stream'])

    def test_existing_api_rejects_error(self):
        from rag_core import call_existing_api
        self.status = 503
        with self.assertRaises(UpstreamError):
            call_existing_api(self.config,'Approval?',self.hits)

    def test_existing_api_rejects_bad_schema(self):
        from rag_core import call_existing_api
        self.payload = {'unexpected':'shape'}
        with self.assertRaises(UpstreamError):
            call_existing_api(self.config,'Approval?',self.hits)

    def test_existing_api_uses_separate_secret(self):
        from rag_core import call_existing_api
        call_existing_api(self.config,'Approval?',self.hits)
        auth = self.captured[0][1]
        self.assertNotEqual(auth,'Bearer '+self.app_secret.read_text())
