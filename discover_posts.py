#!/usr/bin/env python3
"""Discover post URLs from a category/archive page and save a cumulative JSON database."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_TIMEOUT = 30
DEFAULT_DATABASE = Path("data/post_urls.json")
USER_AGENT = "post-url-discoverer/1.0 (+https://github.com/telebottg7-sudo/Cosplay.image)"


class PostCardParser(HTMLParser):
    """Collect links inside archive cards marked with the post-item class."""

    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.div_depth = 0
        self.post_depth = 0
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "div":
            self.div_depth += 1
            if "post-item" in (attributes.get("class") or "").split():
                self.post_depth = self.div_depth
        if tag == "a" and self.post_depth:
            href = attributes.get("href")
            if href:
                self.urls.append(urljoin(self.source_url, href.strip()))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "div":
            if self.post_depth == self.div_depth:
                self.post_depth = 0
            self.div_depth -= 1


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http:// or https:// URL")
    return value


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    validate_url(url)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response.text


def normalize_post_url(value: str, source_url: str) -> str | None:
    parsed = urlparse(value)
    source_host = urlparse(source_url).netloc.lower()
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != source_host:
        return None
    path = parsed.path.rstrip("/")
    if not path or path.startswith(("/category/", "/tag/", "/author/", "/page/", "/feed/", "/wp-")):
        return None
    if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js")):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{path}/"


def discover_post_urls(category_url: str, timeout: int = DEFAULT_TIMEOUT) -> list[str]:
    """Return unique post URLs from archive cards on a category page."""
    html = fetch_html(category_url, timeout)
    parser = PostCardParser(category_url)
    parser.feed(html)
    result: list[str] = []
    seen: set[str] = set()
    for candidate in parser.urls:
        url = normalize_post_url(candidate, category_url)
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def save_to_database(category_url: str, post_urls: list[str], database: Path) -> None:
    """Merge a category discovery into the cumulative JSON database."""
    database.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": 1, "sources": [], "posts": []}
    if database.exists():
        try:
            existing = json.loads(database.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data["sources"] = existing.get("sources", [])
                data["posts"] = existing.get("posts", [])
        except json.JSONDecodeError:
            pass

    discovered_at = datetime.now(timezone.utc).isoformat()
    data["sources"] = [source for source in data["sources"] if source.get("url") != category_url]
    data["sources"].append({"url": category_url, "post_count": len(post_urls), "discovered_at": discovered_at})
    known = {post.get("url"): post for post in data["posts"] if isinstance(post, dict) and post.get("url")}
    for url in post_urls:
        entry = known.setdefault(url, {"url": url, "sources": []})
        if category_url not in entry["sources"]:
            entry["sources"].append(category_url)
        entry["discovered_at"] = discovered_at
    data["posts"] = sorted(known.values(), key=lambda post: post["url"])
    data["post_count"] = len(data["posts"])
    database.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover post URLs from a category page.")
    parser.add_argument("category_url")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()
    if args.timeout <= 0:
        print("error: timeout must be greater than zero", file=sys.stderr)
        return 2
    try:
        urls = discover_post_urls(args.category_url, args.timeout)
        save_to_database(args.category_url, urls, args.database)
    except (ValueError, requests.RequestException, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Discovered {len(urls)} post URL(s); database now contains {json.loads(args.database.read_text())['post_count']} post(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
