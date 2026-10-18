import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from alttext.remote import scan_url


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'<html><body><img src="/a.png"><img src="/b.png" alt="A chart"><img src="data:image/png;base64,AA"></body></html>'
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_scan_url_reports_missing_and_present():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = scan_url(f"http://127.0.0.1:{server.server_port}/")
    finally:
        server.shutdown()
    assert len(result.items) == 2
    assert result.items[0].status == "missing"
    assert result.items[0].ref.endswith("/a.png")
    assert result.items[1].status == "present"


def test_scan_url_rejects_non_http():
    with pytest.raises(ValueError):
        scan_url("file:///tmp/page.html")
