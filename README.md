# HTML Extractor

A small Python command-line tool that downloads the HTML response from an HTTP(S) URL. It follows redirects, sends a descriptive User-Agent, and saves the response body without modifying it.

## Local usage

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python extract_html.py https://example.com --output example.html
```

The output defaults to `page.html` when `--output` is omitted. Use `--timeout` to change the request timeout in seconds.

## GitHub Actions

1. Open the repository's **Actions** tab.
2. Select **Extract HTML**.
3. Choose **Run workflow**.
4. Enter an absolute `http://` or `https://` URL and optionally change the artifact filename.
5. Download the `extracted-html` artifact from the completed workflow run.

The workflow is defined in [`.github/workflows/extract-html.yml`](.github/workflows/extract-html.yml) and is intentionally manual (`workflow_dispatch`) so a URL is supplied for each run.

## Tests

```bash
python -m pip install -r requirements.txt pytest
pytest -q
```

## Notes

- Only `http://` and `https://` URLs are accepted.
- The workflow stores the extracted HTML as an artifact for 7 days.
- The target website may block automated requests or require JavaScript; this tool extracts the server response and does not render a browser page.
