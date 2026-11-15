"""Offline, loopback-only OpenAI-style API test double. Not an AI model."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/v1/models':
            self.send_error(404); return
        self.reply({'data':[{'id':'offline-mock','object':'model'}],'object':'list'})

    def do_POST(self):
        if self.path != '/v1/chat/completions':
            self.send_error(404); return
        length=int(self.headers.get('Content-Length','0'))
        if length <= 0 or length > 16000:
            self.send_error(413); return
        try:
            data=json.loads(self.rfile.read(length))
            if data.get('model') != 'offline-mock':
                self.send_error(400); return
        except (ValueError,TypeError):
            self.send_error(400); return
        self.reply({'id':'offline-mock-response','object':'chat.completion',
                   'choices':[{'index':0,'message':{'role':'assistant',
                      'content':'OFFLINE MOCK RESPONSE. No AI model generated this content.'},
                      'finish_reason':'stop'}]})

    def reply(self, body):
        raw=json.dumps(body).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def log_message(self,fmt,*args):
        pass  # Avoid logging requests in the laboratory double.

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',8767), Handler).serve_forever()
