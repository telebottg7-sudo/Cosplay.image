import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from extract_html import extract_html, validate_url


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"<!doctype html><html><body><h1>Test page</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def test_validate_url_accepts_http_and_https():
    assert validate_url("http://example.com") == "http://example.com"
    assert validate_url("https://example.com/page") == "https://example.com/page"


@pytest.mark.parametrize("url", ["example.com", "ftp://example.com", "", "https://"])
def test_validate_url_rejects_non_http_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_extract_html_writes_response(tmp_path: Path):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        output = tmp_path / "nested" / "page.html"
        size = extract_html(f"http://127.0.0.1:{server.server_port}", output)
        assert output.read_bytes().startswith(b"<!doctype html>")
        assert size == output.stat().st_size
    finally:
        server.shutdown()
        thread.join()
