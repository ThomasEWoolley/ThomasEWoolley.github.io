#!/usr/bin/env python3
"""Build the public sitemap from the main pages and linked teaching resources."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://thomaswoolley.co.uk/"
MAIN_PAGES = ("", "academia.html", "outreach.html", "lecturing.html",
              "apps.html", "codes.html", "contact.html")
# This GitHub Pages project is served separately from the main repository.
GAME_PATH = "/open-learning-material/math-bio-surfers/"


class TeachingLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def sitemap_urls() -> list[str]:
    urls = [SITE_URL + page for page in MAIN_PAGES]
    parser = TeachingLinks()
    parser.feed((ROOT / "lecturing.html").read_text(encoding="utf-8"))
    for href in parser.links:
        parts = urlsplit(urljoin(SITE_URL + "lecturing.html", href))
        if (parts.scheme, parts.netloc) != ("https", "thomaswoolley.co.uk"):
            continue
        if not (parts.path.endswith((".html", ".pdf")) or parts.path == GAME_PATH):
            continue
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        if url not in urls:
            urls.append(url)
    return urls


def render_sitemap() -> str:
    # Omit lastmod rather than publish dates not tied to actual content changes.
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sitemap_urls():
        lines.extend(["  <url>", f"    <loc>{escape(url)}</loc>", "  </url>"])
    return "\n".join(lines + ["</urlset>", ""])


if __name__ == "__main__":
    (ROOT / "sitemap.xml").write_text(render_sitemap(), encoding="utf-8")
    print(f"Wrote {len(sitemap_urls())} public URLs to sitemap.xml.")
