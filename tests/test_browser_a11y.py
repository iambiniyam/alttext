"""Browser-level accessibility checks for alttext."""

from __future__ import annotations

import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import uvicorn

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

from alttext.server import app

AXE = Path(__file__).with_name("axe.min.js")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'<html><body><img src="/a.png"><img src="/b.png" alt="A chart"></body></html>'
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def live_server():
    port = free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def axe_violations(page) -> list[dict]:
    page.add_script_tag(path=str(AXE))
    report = page.evaluate(
        """async () => await axe.run(document, {
          runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] }
        })"""
    )
    return [item for item in report["violations"] if item["impact"] in {"serious", "critical"}]


def test_initial_and_url_audit_states(live_server):
    page_server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=page_server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            tab = browser.new_page(viewport={"width": 1182, "height": 900})
            tab.goto(live_server, wait_until="networkidle")
            assert axe_violations(tab) == []

            tab.fill("#url", f"http://127.0.0.1:{page_server.server_port}/")
            tab.click("#url-go")
            tab.wait_for_selector("#url-result:not([hidden])", timeout=30000)
            assert axe_violations(tab) == []
            browser.close()
    finally:
        page_server.shutdown()
