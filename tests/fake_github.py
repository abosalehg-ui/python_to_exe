"""A local stand-in for the GitHub releases API, for tests.

A real HTTP server (``http.server`` in a thread) that implements the handful
of endpoints the publisher uses, keeps releases and assets in memory, and
records every request — method, path, query, headers and body size — so tests
can assert exactly what was sent. Requests without the expected
``Authorization: Bearer <token>`` get a 401, as on GitHub.
"""

import json
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeGitHub:
    def __init__(self, token: str, repository: str = "me/app"):
        self.token = token
        self.repository = repository
        self.requests = []  # dicts: method, path, query, headers, body_size
        self.releases = []
        self.uploads = {}  # asset name -> bytes
        self._next_id = 100
        self.fail_uploads = set()  # asset names that return 500
        handler = self._handler_class()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def paths(self, method=None):
        return [r["path"] for r in self.requests if method is None or r["method"] == method]

    # ── HTTP ────────────────────────────────────────────────────────────

    def _handler_class(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):  # keep test output clean
                pass

            def _body(self) -> bytes:
                length = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(length) if length else b""

            def _send(self, status, payload=None):
                data = b"" if payload is None else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if data:
                    self.wfile.write(data)

            def _handle(self, method):
                parts = urllib.parse.urlsplit(self.path)
                body = self._body()
                fake.requests.append({
                    "method": method, "path": parts.path,
                    "query": dict(urllib.parse.parse_qsl(parts.query)),
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body_size": len(body), "body": body if len(body) < 4096 else b"",
                })
                if self.headers.get("Authorization") != f"Bearer {fake.token}":
                    return self._send(401, {"message": "Bad credentials"})
                repo = f"/repos/{fake.repository}"
                path = parts.path
                query = dict(urllib.parse.parse_qsl(parts.query))

                m = re.fullmatch(re.escape(repo) + r"/releases/tags/(.+)", path)
                if method == "GET" and m:
                    tag = urllib.parse.unquote(m.group(1))
                    for release in fake.releases:
                        if release["tag_name"] == tag and not release["draft"]:
                            return self._send(200, release)
                    return self._send(404, {"message": "Not Found"})
                if method == "GET" and path == repo + "/releases":
                    return self._send(200, fake.releases)
                if method == "POST" and path == repo + "/releases":
                    payload = json.loads(body.decode("utf-8"))
                    rid = fake._new_id()
                    release = {
                        "id": rid, "tag_name": payload["tag_name"], "name": payload.get("name"),
                        "body": payload.get("body"), "draft": payload.get("draft", False),
                        "prerelease": payload.get("prerelease", False),
                        "target_commitish": payload.get("target_commitish", ""),
                        "html_url": f"https://github.com/{fake.repository}/releases/tag/"
                                    f"{payload['tag_name']}",
                        "upload_url": f"{fake.url}/uploads{repo}/releases/{rid}/assets"
                                      "{?name,label}",
                        "assets": [],
                    }
                    fake.releases.append(release)
                    return self._send(201, release)
                m = re.fullmatch(r"/uploads" + re.escape(repo) + r"/releases/(\d+)/assets", path)
                if method == "POST" and m:
                    name = query.get("name", "")
                    if name in fake.fail_uploads:
                        return self._send(500, {"message": "upload failed"})
                    release = next(r for r in fake.releases if r["id"] == int(m.group(1)))
                    tag = release["tag_name"]
                    asset = {
                        "id": fake._new_id(), "name": name, "size": len(body),
                        "content_type": self.headers.get("Content-Type"),
                        "browser_download_url": f"https://github.com/{fake.repository}/"
                                                f"releases/download/{tag}/{name}",
                    }
                    release["assets"].append(asset)
                    fake.uploads[name] = body
                    return self._send(201, asset)
                m = re.fullmatch(re.escape(repo) + r"/releases/assets/(\d+)", path)
                if method == "DELETE" and m:
                    for release in fake.releases:
                        release["assets"] = [a for a in release["assets"]
                                             if a["id"] != int(m.group(1))]
                    return self._send(204)
                return self._send(404, {"message": "Not Found"})

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_DELETE(self):
                self._handle("DELETE")

        return Handler
