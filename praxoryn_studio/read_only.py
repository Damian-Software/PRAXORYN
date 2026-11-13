"""Read-only loopback API; frontends are not allowed to change job state."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from .engine import list_jobs, get_job, JobError


def serve(home: Path, port: int = 8769):
    token=os.environ.get('STUDIO_READ_TOKEN', '')
    if len(token)<24:
        raise ValueError('STUDIO_READ_TOKEN must be at least 24 characters')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Deliberately do not log requests, IPs or query strings in this lab.
            pass
        def send_json(self,code,data):
            raw=json.dumps(data,separators=(',',':')).encode()
            self.send_response(code)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not hmac.compare_digest(self.headers.get('X-Read-Token',''),token):
                self.send_json(401,{'error':'unauthorized'});return
            parts=urlsplit(self.path)
            if parts.path=='/healthz':
                self.send_json(200,{'status':'ok'});return
            query=parse_qs(parts.query)
            tenant=query.get('tenant',[''])[0]
            try:
                if parts.path=='/jobs':
                    value={'jobs':list_jobs(home,tenant)}
                elif parts.path.startswith('/jobs/'):
                    job_id=parts.path[len('/jobs/'):]
                    value=get_job(home,tenant,job_id)
                else:
                    self.send_json(404,{'error':'not_found'});return
            except (ValueError,JobError,FileNotFoundError):
                self.send_json(404,{'error':'not_found'});return
            self.send_json(200,value)
        def do_POST(self):
            self.send_json(405,{'error':'method_not_allowed'})
    print(f'Read-only dashboard API at http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
