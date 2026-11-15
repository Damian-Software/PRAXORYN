"""Deterministic loopback-only fake model for offline exercises; never expose."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        # Intentionally no HTTP access logging of paths or content in this lab.
        pass

    def write_json(self, status, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self.write_json(200, {"status": "ok"})
        elif self.path == "/v1/models":
            self.write_json(200, {"data": [{"id": "mock-model"}]})
        else:
            self.write_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.write_json(404, {"error": "not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 16384:
                self.write_json(413, {"error": "body too large"})
                return
            obj = json.loads(self.rfile.read(size))
            if obj.get("model") != "mock-model":
                self.write_json(404, {"error": "unknown model"})
                return
        except (ValueError, AttributeError, TypeError):
            self.write_json(400, {"error": "invalid body"})
            return
        self.write_json(200, {"choices": [{"message": {"content": "READY"}}]})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Mock API bound to 127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
