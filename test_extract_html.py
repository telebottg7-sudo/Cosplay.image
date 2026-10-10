import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from extract_html import extract_image_urls, extract_images, validate_url, write_json_chunks


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b'''<!doctype html>
        <html><head><meta property="og:image" content="/images/meta.png"></head>
        <body>
          <img src="/images/one.webp">
          <img src="https://cdn.example.com/two.jpg?size=large">
          <img src="/not-an-image.html">
          <img srcset="/images/three.png 1x, /images/four.gif 2x">
          <a href="https://example.com/page.html">Other link</a>
        </body></html>'''
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


def test_extract_image_urls_filters_other_links_and_resolves_relative_urls():
    html = '<img src="/images/one.webp"><a href="/page.html">page</a><img src="/images/one.webp">'
    assert extract_image_urls(html, "https://example.com/post") == ["https://example.com/images/one.webp"]


def test_write_json_chunks_limits_each_file_to_chunk_size(tmp_path: Path):
    urls = [f"https://example.com/{index}.webp" for index in range(401)]
    paths = write_json_chunks(urls, tmp_path / "image", chunk_size=200)
    assert [path.name for path in paths] == ["chunk1.json", "chunk2.json", "chunk3.json"]
    assert [len(json.loads(path.read_text())) for path in paths] == [200, 200, 1]
    assert json.loads(paths[0].read_text())[0] == urls[0]
    assert json.loads(paths[-1].read_text())[-1] == urls[-1]
    manifest = json.loads((tmp_path / "image" / "manifest.json").read_text())
    assert manifest == {"chunks": ["chunk1.json", "chunk2.json", "chunk3.json"], "count": 401, "chunk_size": 200}


def test_extract_images_writes_json_chunks(tmp_path: Path):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        paths = extract_images(f"http://127.0.0.1:{server.server_port}", tmp_path / "image")
        assert len(paths) == 1
        urls = json.loads(paths[0].read_text())
        assert urls == [
            "http://127.0.0.1:%s/images/four.gif" % server.server_port,
            "http://127.0.0.1:%s/images/meta.png" % server.server_port,
            "http://127.0.0.1:%s/images/one.webp" % server.server_port,
            "http://127.0.0.1:%s/images/three.png" % server.server_port,
            "https://cdn.example.com/two.jpg?size=large",
        ]
    finally:
        server.shutdown()
        thread.join()
