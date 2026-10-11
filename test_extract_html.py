import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from extract_html import extract_image_urls, extract_images, page_slug, read_urls_file, validate_url, write_json_chunks
from discover_posts import PostCardParser, save_to_database


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b'''<!doctype html>
        <html><body>
          <article>
            <img src="/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-1_result.webp">
            <img srcset="/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-2_result.webp 1x, /wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-3_result.webp 2x">
            <a href="/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-4_result.webp">Image</a>
            <img src="/wp-content/themes/flatsome/assets/css/icons/fl-icons.svg">
          </article>
          <aside><img src="/wp-content/uploads/2026/08/related-post.webp"></aside>
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


def test_page_slug_uses_the_url_path():
    assert page_slug("https://cosplaytele.com/cyrene-swimsuit/") == "cyrene-swimsuit"
    assert page_slug("https://cosplaytele.com/") == "cosplaytele-com"


def test_read_urls_file_accepts_up_to_20_urls(tmp_path: Path):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("\nhttps://example.com/one\nhttps://example.com/two\n")
    assert read_urls_file(urls_file) == ["https://example.com/one", "https://example.com/two"]


def test_read_urls_file_rejects_more_than_20_urls(tmp_path: Path):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("\n".join(f"https://example.com/{index}" for index in range(21)))
    with pytest.raises(ValueError, match="at most 20"):
        read_urls_file(urls_file)


def test_discover_parser_collects_only_post_card_links():
    parser = PostCardParser("https://example.com/category/demo/")
    parser.feed('''<nav><a href="https://example.com/menu/">Menu</a></nav>
      <div class="col post-item"><a href="/first-post/">First</a></div>
      <div class="col post-item"><a href="/second-post/">Second</a></div>''')
    assert parser.urls == ["https://example.com/first-post/", "https://example.com/second-post/"]


def test_post_database_merges_sources_without_duplicate_posts(tmp_path: Path):
    database = tmp_path / "data" / "post_urls.json"
    save_to_database("https://example.com/category/one/", ["https://example.com/first/"], database)
    save_to_database("https://example.com/category/two/", ["https://example.com/first/", "https://example.com/second/"], database)
    data = json.loads(database.read_text())
    assert data["post_count"] == 2
    assert len(data["sources"]) == 2
    first = next(post for post in data["posts"] if post["url"].endswith("/first/"))
    assert len(first["sources"]) == 2


def test_extract_image_urls_keeps_primary_article_images_only():
    html = '''<html><body><article>
      <img src="/wp-content/uploads/2026/08/one.webp">
      <img src="/wp-content/themes/flatsome/icon.svg">
    </article><div class="related"><img src="/wp-content/uploads/2026/08/related.webp"></div></body></html>'''
    assert extract_image_urls(html, "https://example.com/post") == [
        "https://example.com/wp-content/uploads/2026/08/one.webp"
    ]


def test_write_json_chunks_limits_each_file_to_chunk_size(tmp_path: Path):
    urls = [f"https://example.com/{index}.webp" for index in range(401)]
    paths = write_json_chunks(urls, tmp_path / "image", chunk_size=200)
    assert [path.name for path in paths] == ["chunk1.json", "chunk2.json", "chunk3.json"]
    assert [len(json.loads(path.read_text())) for path in paths] == [200, 200, 1]
    assert json.loads(paths[0].read_text())[0] == urls[0]
    assert json.loads(paths[-1].read_text())[-1] == urls[-1]
    manifest = json.loads((tmp_path / "image" / "manifest.json").read_text())
    assert manifest == {"chunks": ["chunk1.json", "chunk2.json", "chunk3.json"], "count": 401, "chunk_size": 200}


def test_extract_images_writes_only_article_json_urls(tmp_path: Path):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        paths = extract_images(f"http://127.0.0.1:{server.server_port}", tmp_path / "image")
        urls = json.loads(paths[0].read_text())
        host = f"http://127.0.0.1:{server.server_port}"
        assert urls == [
            f"{host}/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-1_result.webp",
            f"{host}/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-2_result.webp",
            f"{host}/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-3_result.webp",
            f"{host}/wp-content/uploads/2026/08/Machi-cosplay-Cyrene-Swimsuit-4_result.webp",
        ]
    finally:
        server.shutdown()
        thread.join()


def test_extract_images_preserves_each_post_in_its_own_folder(tmp_path: Path):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        extract_images(f"{base}/cyrene-swimsuit/", tmp_path / "image")
        extract_images(f"{base}/nahida-30/", tmp_path / "image")
        catalog = json.loads((tmp_path / "image" / "manifest.json").read_text())
        assert [post["slug"] for post in catalog["posts"]] == ["cyrene-swimsuit", "nahida-30"]
        assert (tmp_path / "image" / "cyrene-swimsuit" / "chunk1.json").exists()
        assert (tmp_path / "image" / "nahida-30" / "chunk1.json").exists()
    finally:
        server.shutdown()
        thread.join()
