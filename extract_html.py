#!/usr/bin/env python3
"""Fetch a URL and save its HTML response to a file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

DEFAULT_TIMEOUT = 30
DEFAULT_USER_AGENT = "html-extractor/1.0 (+https://github.com/telebottg7-sudo/Cosplay.image)"


def validate_url(value: str) -> str:
    """Return a valid HTTP(S) URL or raise ValueError."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http:// or https:// URL")
    return value


def extract_html(url: str, output: Path, timeout: int = DEFAULT_TIMEOUT) -> int:
    """Fetch *url*, write the response body to *output*, and return its byte count."""
    validate_url(url)
    response = requests.get(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=timeout,
        allow_redirects=True,
    )
    response.raise_for_status()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    return len(response.content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract HTML from a web URL.")
    parser.add_argument("url", help="Absolute http:// or https:// URL to fetch")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("page.html"),
        help="Output filename (default: page.html)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.timeout <= 0:
        print("error: timeout must be greater than zero", file=sys.stderr)
        return 2
    try:
        size = extract_html(args.url, args.output, args.timeout)
    except (ValueError, requests.RequestException, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Saved {size} bytes from {args.url} to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
