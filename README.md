# Cosplay Image Archive

A static GitHub Pages gallery for image URLs extracted from web pages. The extractor keeps only primary page/gallery images, removes duplicates and site assets, and permanently archives every scraped post.

## Workflow: discover post URLs

Use **Actions → Discover Post URLs → Run workflow** and enter a category or archive URL such as:

```text
https://cosplaytele.com/category/byoru/
```

The workflow finds post-card links and saves a cumulative repository database at:

```text
data/post_urls.json
```

It records each post URL, the category sources where it was found, and discovery timestamps. Re-discovering a category updates the existing entries without duplicating them.

## Workflow: extract saved posts

Use **Actions → Extract Image URLs → Run workflow**, enable **Use saved post URLs from data/post_urls.json**, and choose:

- `database_offset`: starting post index
- `database_limit`: number of posts to process, maximum 20

For a category with 67 posts, run four batches with offsets `0`, `20`, `40`, and `60`. Each post is saved in its own archive folder under `image/`.

You can also leave database mode disabled and paste up to 20 direct post URLs into the multiline **URLs** field.

## Local usage

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python discover_posts.py https://cosplaytele.com/category/byoru/
python extract_html.py --database data/post_urls.json --offset 0 --limit 20
```

Each URL is saved in its own folder based on the page slug:

```text
image/
├── manifest.json
├── cyrene-swimsuit/
│   ├── manifest.json
│   └── chunk1.json
└── nahida-30/
    ├── manifest.json
    └── chunk1.json
```

Running the extractor for a new URL does not overwrite other posts. Running it again for the same page updates only that page's folder. Duplicate image URLs are filtered both within each page and across the entire archive, so the same image is stored only once.

## Gallery frontend

The gallery reads every post in `image/manifest.json` and displays all archived images together with pagination. Clicking an image opens its original URL in a new tab.

## GitHub Pages

The `Deploy Gallery to GitHub Pages` workflow publishes the complete static site whenever the frontend or `image/` archive changes. The published address is:

```text
https://telebottg7-sudo.github.io/Cosplay.image/
```

## Notes

- Only `http://` and `https://` source URLs are accepted.
- Database extraction accepts a maximum of 20 posts per run.
- A dedicated WordPress gallery is preferred; otherwise the primary article is used.
- Image URLs must come from the same host as the provided page.
- WordPress theme/plugin assets and common site icons are excluded.
- The extractor reads the server response and does not render JavaScript.
- Images remain property of their original publishers.
