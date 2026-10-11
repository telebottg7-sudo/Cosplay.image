#!/usr/bin/env python3
"""Fetch a web page, extract its primary content image URLs, and write JSON chunks."""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_TIMEOUT = 30
DEFAULT_CHUNK_SIZE = 200
DEFAULT_OUTPUT_DIR = Path("image")
DEFAULT_USER_AGENT = "html-image-extractor/1.0 (+https://github.com/telebottg7-sudo/Cosplay.image)"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".ico", ".tif", ".tiff")
EXCLUDED_PATH_PARTS = ("/wp-content/themes/", "/wp-content/plugins/", "/wp-includes/")
EXCLUDED_FILENAME_PARTS = ("favicon", "cropped-icon", "site-icon", "logo", "avatar", "gravatar")


def validate_url(value: str) -> str:
    """Return a valid HTTP(S) URL or raise ValueError."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http:// or https:// URL")
    return value


def is_image_url(value: str, page_url: str) -> bool:
    """Return whether a URL is a page image rather than a theme or site icon asset."""
    parsed = urlparse(value)
    path = parsed.path.lower()
    filename = Path(parsed.path).name.lower()
    page_host = urlparse(page_url).netloc.lower().split(":", 1)[0]
    image_host = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme not in {"http", "https"} or image_host != page_host:
        return False
    if not path.endswith(IMAGE_EXTENSIONS) or any(part in path for part in EXCLUDED_PATH_PARTS):
        return False
    return not any(part in filename for part in EXCLUDED_FILENAME_PARTS)


class ImageURLParser(HTMLParser):
    """Collect image URLs from the primary article, not the site chrome/sidebar."""

    ATTRIBUTES = {"src", "data-src", "data-lazy-src", "data-original", "href", "content"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, page_url: str, scope_tag: str = "article") -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.scope_tag = scope_tag
        self.scope_active = False
        self.scope_depth = 0
        self.urls: list[str] = []
        self.seen: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        class_names = {value for name, value in attrs if name.lower() == "class" and value for value in value.lower().split()}
        if self.scope_tag == "gallery" and not self.scope_active and tag == "div" and "gallery" in class_names:
            self.scope_active = True
            self.scope_depth = 1
        elif self.scope_tag != "gallery" and tag == self.scope_tag:
            self.scope_active = True
        elif self.scope_tag == "gallery" and self.scope_active and tag not in self.VOID_TAGS:
            self.scope_depth += 1
        if not self.scope_active:
            return
        for name, value in attrs:
            if not value or name.lower() not in self.ATTRIBUTES:
                continue
            self._add_candidate(value)
        for name, value in attrs:
            if name.lower() == "srcset" and value:
                for candidate in value.split(","):
                    self._add_candidate(candidate.strip().split()[0])
    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.scope_tag == "gallery" and self.scope_active and tag not in self.VOID_TAGS:
            self.scope_depth -= 1
            if self.scope_depth <= 0:
                self.scope_active = False
                self.scope_depth = 0
        elif self.scope_tag != "gallery" and tag == self.scope_tag:
            self.scope_active = False

    def _add_candidate(self, candidate: str) -> None:
        absolute = urljoin(self.page_url, candidate.strip())
        if is_image_url(absolute, self.page_url) and absolute not in self.seen:
            self.seen.add(absolute)
            self.urls.append(absolute)


def choose_scope_tag(html: str) -> str:
    """Prefer a dedicated gallery, then article markup, falling back to main/body."""
    lowered = html.lower()
    if 'class="gallery' in lowered or "class='gallery" in lowered:
        return "gallery"
    if "<article" in lowered:
        return "article"
    if "<main" in lowered:
        return "main"
    return "body"


def extract_image_urls(html: str, page_url: str) -> list[str]:
    """Extract unique, same-site image URLs from the primary page content."""
    parser = ImageURLParser(page_url, choose_scope_tag(html))
    parser.feed(html)
    return parser.urls


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch and return the response body as text."""
    validate_url(url)
    response = requests.get(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=timeout,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def write_json_chunks(urls: list[str], output_dir: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[Path]:
    """Write URLs to chunk files plus a manifest, and return written paths."""
    if chunk_size <= 0:
        raise ValueError("chunk size must be greater than zero")
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_chunk in output_dir.glob("chunk*.json"):
        old_chunk.unlink()
    paths: list[Path] = []
    for start in range(0, len(urls), chunk_size):
        path = output_dir / f"chunk{start // chunk_size + 1}.json"
        path.write_text(json.dumps(urls[start : start + chunk_size], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(path)
    manifest = {"chunks": [path.name for path in paths], "count": len(urls), "chunk_size": chunk_size}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def extract_images(url: str, output_dir: Path, timeout: int = DEFAULT_TIMEOUT, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[Path]:
    """Fetch *url*, extract its primary-content image URLs, and write JSON chunks."""
    html = fetch_html(url, timeout)
    urls = extract_image_urls(html, url)
    return write_json_chunks(urls, output_dir, chunk_size)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract primary-content image URLs into JSON chunks.")
    parser.add_argument("url", help="Absolute http:// or https:// URL to scan")
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory (default: image)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Maximum image URLs per JSON file (default: 200)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.timeout <= 0 or args.chunk_size <= 0:
        print("error: timeout and chunk size must be greater than zero", file=sys.stderr)
        return 2
    try:
        paths = extract_images(args.url, args.output_dir, args.timeout, args.chunk_size)
    except (ValueError, requests.RequestException, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Extracted image URLs into {len(paths)} JSON file(s) in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
