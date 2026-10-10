# HTML Image URL Extractor

A small Python tool that downloads a web page and extracts only image URLs from its HTML. It removes other links, deduplicates image URLs, resolves relative image paths, and writes JSON files containing at most 200 URLs each.

## Local usage

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python extract_html.py https://example.com
```

By default, the output is written to:

```text
image/chunk1.json
image/chunk2.json
...
```

Each JSON file contains a simple array of image URL strings. The default maximum is 200 URLs per file; customize it with `--chunk-size`:

```bash
python extract_html.py https://example.com --output-dir image --chunk-size 200
```

Supported image extensions include `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.avif`, `.bmp`, `.ico`, `.tif`, and `.tiff`. URLs with query strings are supported.

## GitHub Actions

1. Open the repository's **Actions** tab.
2. Select **Extract Image URLs**.
3. Choose **Run workflow**.
4. Enter an absolute `http://` or `https://` URL.
5. Optionally change the maximum chunk size; it defaults to 200.
6. Download the `image-url-chunks` artifact, or find the generated files committed under `image/` on the repository's `main` branch.

The workflow is defined in [`.github/workflows/extract-html.yml`](.github/workflows/extract-html.yml). It is manually triggered and commits changed JSON chunks to the repository after each run.

## Tests

```bash
python -m pip install -r requirements.txt pytest
pytest -q
```

## Notes

- Only `http://` and `https://` source URLs are accepted.
- The extractor reads the server response and does not render JavaScript.
- Some sites may block automated requests or load images only after JavaScript runs.
- The workflow requires repository `contents: write` permission to save generated chunks to `image/`.
