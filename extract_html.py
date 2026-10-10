#!/usr/bin/env python3
"""Fetch a web page, extract image URLs, and write them as JSON chunks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_TIMEOUT = 30
DEFAULT_CHUNK_SIZE = 200
DEFAULT_OUTPUT_DIR = Path("image")
DEFAULT_USER_AGENT = "html-image-extractor/1.0 (+https://github.com/telebottg7-sudo/Cosplay.image)"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif", ".bmp", ".ico", ".tif", ".tiff")
ABSOLUTE_URL_PATTERN = re.compile(r"https?://[^\s\"'<>\\)]+", re.IGNORECASE)


def validate_url(value: str) -> str:
    """Return a valid HTTP(S) URL or raise ValueError."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http:// or https:// URL")
    return value


def is_image_url(value: str) -> bool:
    """Return whether a URL path ends in a supported image extension."""
    path = urlparse(value).path.lower()
    return path.endswith(IMAGE_EXTENSIONS)


class ImageURLParser(HTMLParser):
    """Collect image URLs from common HTML image attributes and metadata."""

    ATTRIBUTES = {"src", "data-src", "data-lazy-src", "data-original", "href", "content"}

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.urls: set[str] = set()

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if not value or name.lower() not in self.ATTRIBUTES:
                continue
            self._add_candidate(value)
        for name, value in attrs:
            if name.lower() == "srcset" and value:
                for candidate in value.split(","):
                    self._add_candidate(candidate.strip().split()[0])

    def _add_candidate(self, candidate: str) -> None:
        absolute = urljoin(self.page_url, candidate)
        if is_image_url(absolute):
            self.urls.add(absolute)


def extract_image_urls(html: str, page_url: str) -> list[str]:
    """Extract unique absolute image URLs from HTML in stable sorted order."""
    parser = ImageURLParser(page_url)
    parser.feed(html)
    for candidate in ABSOLUTE_URL_PATTERN.findall(html):
        candidate = candidate.rstrip(".,;:")
        if is_image_url(candidate):
            parser.urls.add(candidate)
    return sorted(parser.urls)


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
    """Write URLs to chunk files plus a manifest, and return chunk paths."""
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
    manifest = {
        "chunks": [path.name for path in paths],
        "count": len(urls),
        "chunk_size": chunk_size,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def extract_images(url: str, output_dir: Path, timeout: int = DEFAULT_TIMEOUT, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[Path]:
    """Fetch *url*, extract its image URLs, and write JSON chunks."""
    html = fetch_html(url, timeout)
    urls = extract_image_urls(html, url)
    return write_json_chunks(urls, output_dir, chunk_size)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract image URLs from a web page into JSON chunks.")
    parser.add_argument("url", help="Absolute http:// or https:// URL to scan")
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory (default: image)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Maximum URLs per JSON file (default: 200)")
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
