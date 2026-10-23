# Thomas E. Woolley academic website

This repository contains the static files for [thomaswoolley.co.uk](https://thomaswoolley.co.uk). GitHub Pages serves the site directly from the repository root.

## Local preview

From the repository root, run:

```sh
python -m http.server 8000
```

Then open `http://localhost:8000` in a browser.

## Site checks

Run the built-in checker before publishing:

```sh
python scripts/check_site.py
```

It checks internal links and fragments, referenced local assets, LaTeX image paths, duplicate element IDs, key page metadata, image alternative text, iframe titles, and insecure asset URLs. The same command runs automatically for pushes and pull requests through GitHub Actions.

## Structure

- Root HTML files contain the main public pages.
- `assets/css/` contains the shared stylesheets.
- `assets/images/` contains optimised images used by the main pages.
- `Q1/` to `Q5/` contain downloadable and online teaching sheets.
- `Pictures/` contains figures used by the teaching material.
- `files/Master_2.pdf` contains the lecture notes.
- `scripts/check_site.py` validates the static site.

## Updating the outreach archive

Edit `data/outreach-media.json` to add or amend a YouTube video or Instagram post. Use an ISO publication date (`YYYY-MM-DD`) and a unique platform/ID pair. Instagram entries can also include a short description and `kind` (`Reel` or `Post`).

Regenerate the static page and check all local links:

```sh
python scripts/render_outreach_media.py
python scripts/check_site.py
```

The renderer sorts entries newest first, groups them by year, and preserves the rest of the outreach page. The recorded dates are platform publication dates, which can differ from the dates of talks or events.
