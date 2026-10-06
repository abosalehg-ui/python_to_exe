"""A local HTTP server for the updater tests (``http.server`` in a thread).

Serves a dictionary of path → response; records every request so a test can
prove that a refused URL was never even contacted.
"""

import http.server
import threading
from typing import Dict, List, Tuple


class UpdateServer:
    def __init__(self):
        #: path → (status, headers, body)
        self.routes: Dict[str, Tuple[int, Dict[str, str], bytes]] = {}
        self.requests: List[str] = []
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # http.server's naming
                server.requests.append(self.path)
                status, headers, body = server.routes.get(self.path, (404, {}, b"not found"))
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(
            target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
        )

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def serve(self, path: str, body: bytes, status: int = 200, **headers: str) -> str:
        self.routes[path] = (status, dict(headers), body)
        return self.url(path)

    def redirect(self, path: str, location: str) -> str:
        self.routes[path] = (302, {"Location": location}, b"")
        return self.url(path)

    def __enter__(self) -> "UpdateServer":
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.httpd.shutdown()
        self.httpd.server_close()
