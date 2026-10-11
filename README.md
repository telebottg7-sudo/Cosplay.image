# Cosplay Image Archive

A static GitHub Pages gallery for image URLs extracted from web pages. The extractor keeps only primary page/gallery images, removes duplicates and site assets, and permanently archives every scraped post.

## Extract image URLs

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python extract_html.py https://example.com/post-name/
```

Each URL is saved in its own folder based on the page slug:

```text
image/manifest.json                         # cumulative catalog of all posts
image/cyrene-swimsuit/manifest.json         # this post's metadata
image/cyrene-swimsuit/chunk1.json
image/nahida-30/manifest.json               # another post's metadata
image/nahida-30/chunk1.json
```

Running the extractor for a new URL **does not overwrite other posts**. Running it again for the same page updates only that page's folder, which prevents duplicate archive entries while allowing refreshed source content. Each post's chunks contain at most 200 image URL strings.

The root `image/manifest.json` contains a `posts` catalog. The frontend reads every post in that catalog and displays all archived images together.

## Gallery frontend

The static frontend consists of:

- `index.html` — accessible gallery shell
- `styles.css` — responsive visual design
- `app.js` — cumulative manifest loading, image rendering, and pagination

The gallery displays 24 images per page across all archived posts. Clicking an image opens its original URL in a new tab.

## GitHub Actions

### Extract image URLs

1. Open the repository's **Actions** tab.
2. Select **Extract Image URLs**.
3. Choose **Run workflow**.
4. Enter an absolute `http://` or `https://` URL.
5. Optionally change the maximum chunk size.

The workflow uploads the complete `image/` archive as an artifact and commits only the new or updated post folder plus the cumulative manifest. Existing post folders remain in the repository.

### Deploy GitHub Pages

The `Deploy Gallery to GitHub Pages` workflow publishes the complete static site whenever the frontend or `image/` archive changes. In repository settings, set:

**Settings → Pages → Build and deployment → Source: GitHub Actions**

The published address is:

```text
https://telebottg7-sudo.github.io/Cosplay.image/
```

## Tests

```bash
python -m pip install -r requirements.txt pytest
pytest -q
```

## Notes

- Only `http://` and `https://` source URLs are accepted.
- A dedicated WordPress gallery is preferred; otherwise the primary article is used.
- Image URLs must come from the same host as the provided page.
- WordPress theme/plugin assets and common site icons are excluded.
- The extractor reads the server response and does not render JavaScript.
- Images remain property of their original publishers.
