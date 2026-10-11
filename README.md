# Cosplay Image Archive

A static GitHub Pages gallery for image URLs extracted from web pages. The extractor keeps only image URLs, removes duplicates, and writes JSON chunks of up to 200 URLs. The frontend reads those chunks, displays a responsive gallery, and provides pagination.

## Extract image URLs

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python extract_html.py https://example.com
```

The output is written to:

```text
image/manifest.json
image/chunk1.json
image/chunk2.json
...
```

Each chunk contains at most 200 image URL strings. Customize the output location or chunk size with `--output-dir` and `--chunk-size`.

## Gallery frontend

The static frontend consists of:

- `index.html` — accessible gallery shell
- `styles.css` — responsive visual design
- `app.js` — manifest loading, image rendering, and pagination

The gallery displays 24 images per page. It reads `image/manifest.json`, loads every listed chunk, deduplicates the URLs again in the browser, and creates page navigation automatically. Clicking an image opens its original URL in a new tab.

If no extraction has been run yet, the frontend displays a clear index-unavailable message instead of failing silently.

## GitHub Actions

### Extract image URLs

1. Open the repository's **Actions** tab.
2. Select **Extract Image URLs**.
3. Choose **Run workflow**.
4. Enter an absolute `http://` or `https://` URL.
5. Optionally change the maximum chunk size.

The workflow uploads an `image-url-chunks` artifact and commits changed JSON files under `image/`. A push to `main` then triggers the Pages deployment workflow.

### Deploy GitHub Pages

The `Deploy Gallery to GitHub Pages` workflow publishes the repository as a static site whenever the frontend or `image/` data changes. In repository settings, set:

**Settings → Pages → Build and deployment → Source: GitHub Actions**

The published address will normally be:

```text
https://telebottg7-sudo.github.io/Cosplay.image/
```

The workflow is defined in [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml).

## Tests

```bash
python -m pip install -r requirements.txt pytest
pytest -q
```

## Notes

- Only `http://` and `https://` source URLs are accepted.
- Supported image extensions include `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.avif`, `.bmp`, `.ico`, `.tif`, and `.tiff`.
- The extractor reads the primary `<article>` content when available, so related posts, sidebars, and theme assets are excluded.
- Image URLs must come from the same host as the provided page; WordPress theme/plugin assets and common site icons are excluded.
- The extractor reads the server response and does not render JavaScript.
- Images remain property of their original publishers.
