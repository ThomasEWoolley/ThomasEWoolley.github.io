#!/usr/bin/env python3
"""Validate local references and essential static-site markup."""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from build_sitemap import GAME_PATH, SITE_URL, render_sitemap, sitemap_urls


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = {
    "404.html",
    "academia.html",
    "apps.html",
    "codes.html",
    "contact.html",
    "index.html",
    "lecturing.html",
    "outreach.html",
}
REFERENCE_ATTRIBUTES = {"action", "href", "poster", "src"}
IGNORED_SCHEMES = {"data", "javascript", "mailto", "sms", "tel"}
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
TEX_GRAPHIC = re.compile(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}")


class PageParser(HTMLParser):
    def __init__(self, relative_path: str) -> None:
        super().__init__(convert_charrefs=True)
        self.relative_path = relative_path
        self.ids: list[str] = []
        self.references: list[tuple[str, str, str, int]] = []
        self.errors: list[str] = []
        self.h1_count = 0
        self.html_lang = ""
        self.has_charset = False
        self.has_viewport = False
        self.has_description = False
        self.has_canonical = False
        self.canonical_urls: list[str] = []
        self.noindex = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        tag = tag.lower()
        line = self.getpos()[0]

        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        anchor_name = values.get("name") if tag == "a" else ""
        if anchor_name:
            self.ids.append(anchor_name)

        if tag == "html":
            self.html_lang = values.get("lang", "")
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            if "charset" in values:
                self.has_charset = True
            name = values.get("name", "").lower()
            if name == "viewport":
                self.has_viewport = True
            elif name == "description" and values.get("content", "").strip():
                self.has_description = True
            elif name in {"robots", "googlebot"}:
                directives = re.split(r"[\s,]+", values.get("content", "").lower())
                self.noindex |= bool({"noindex", "none"}.intersection(directives))
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.has_canonical = bool(values.get("href", "").strip())
            self.canonical_urls.append(values.get("href", "").strip())

        if tag == "img" and "alt" not in values:
            self.errors.append(f"{self.relative_path}:{line}: image is missing alt text")
        if tag == "iframe" and not values.get("title", "").strip():
            self.errors.append(f"{self.relative_path}:{line}: iframe is missing a title")
        if tag == "a" and values.get("target", "").lower() == "_blank":
            rel_values = set(values.get("rel", "").lower().split())
            if "noopener" not in rel_values:
                self.errors.append(f"{self.relative_path}:{line}: target=_blank link needs rel=noopener")

        for attribute in REFERENCE_ATTRIBUTES:
            value = values.get(attribute)
            if value is not None:
                self.references.append((tag, attribute, value.strip(), line))

        srcset = values.get("srcset", "")
        if srcset:
            for candidate in srcset.split(","):
                url = candidate.strip().split()[0]
                self.references.append((tag, "srcset", url, line))


def parse_pages() -> tuple[dict[str, PageParser], list[str]]:
    pages: dict[str, PageParser] = {}
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.html")):
        relative = path.relative_to(ROOT).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{relative}: file is not UTF-8")
            continue
        parser = PageParser(relative)
        try:
            parser.feed(source)
            parser.close()
        except Exception as exc:
            errors.append(f"{relative}: HTML parsing failed: {exc}")
            continue
        duplicates = sorted(name for name, count in Counter(parser.ids).items() if count > 1)
        for duplicate in duplicates:
            errors.append(f"{relative}: duplicate id or anchor name #{duplicate}")
        errors.extend(parser.errors)
        pages[relative] = parser
    return pages, errors


def resolve_local(source: Path, raw_url: str) -> tuple[Path, str] | None:
    if not raw_url or raw_url.startswith("//"):
        return None
    parts = urlsplit(raw_url)
    if parts.scheme.lower() in IGNORED_SCHEMES or parts.scheme or parts.netloc:
        return None
    decoded_path = unquote(parts.path)
    if decoded_path.startswith("/"):
        target = ROOT / decoded_path.lstrip("/")
    elif decoded_path:
        target = source.parent / decoded_path
    else:
        target = source
    target = target.resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        return Path("/__outside_site__"), parts.fragment
    if target.is_dir():
        target /= "index.html"
    return target, unquote(parts.fragment)


def check_references(pages: dict[str, PageParser]) -> list[str]:
    errors: list[str] = []
    for relative, parser in pages.items():
        source = ROOT / relative
        for tag, attribute, url, line in parser.references:
            resolved = resolve_local(source, url)
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.exists():
                errors.append(f"{relative}:{line}: broken {attribute} on <{tag}>: {url or '[empty]'}")
                continue
            if fragment and target.suffix.lower() in {".html", ".htm"}:
                try:
                    target_relative = target.relative_to(ROOT).as_posix()
                except ValueError:
                    continue
                target_page = pages.get(target_relative)
                if target_page is not None and fragment not in target_page.ids:
                    errors.append(f"{relative}:{line}: missing fragment #{fragment} in {target_relative}")
    return errors


def check_public_pages(pages: dict[str, PageParser]) -> list[str]:
    errors: list[str] = []
    for relative in sorted(PUBLIC_PAGES):
        parser = pages.get(relative)
        if parser is None:
            errors.append(f"{relative}: public page is missing or unreadable")
            continue
        requirements = {
            "a UTF-8 charset declaration": parser.has_charset,
            "a viewport meta tag": parser.has_viewport,
            "a description meta tag": parser.has_description,
            "a canonical link": parser.has_canonical,
            "lang=en-GB on the html element": parser.html_lang.lower() == "en-gb",
            "exactly one h1": parser.h1_count == 1,
        }
        for description, passed in requirements.items():
            if not passed:
                errors.append(f"{relative}: expected {description}")
    return errors


def check_stylesheets() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.css")):
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")
        for match in CSS_URL.finditer(source):
            url = match.group(2).strip()
            resolved = resolve_local(path, url)
            if resolved is not None and not resolved[0].exists():
                line = source.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line}: broken CSS url(): {url}")
    return errors


def check_sitemap(pages: dict[str, PageParser]) -> list[str]:
    errors: list[str] = []
    path = ROOT / "sitemap.xml"
    if not path.is_file() or path.read_text(encoding="utf-8") != render_sitemap():
        errors.append("sitemap.xml: missing or stale; run python scripts/build_sitemap.py")
    for url in sitemap_urls():
        parts = urlsplit(url)
        if parts.path == GAME_PATH:
            continue  # Checked on the live site; belongs to another repository.
        relative = unquote(parts.path).lstrip("/") or "index.html"
        target = ROOT / relative
        if not target.is_file():
            errors.append(f"sitemap.xml: missing public resource {relative}")
        parser = pages.get(relative)
        if relative.endswith(".html"):
            if parser is None or parser.canonical_urls != [url]:
                errors.append(f"{relative}: expected exactly one canonical link to {url}")
            if parser is not None and parser.noindex:
                errors.append(f"{relative}: sitemap page must not have noindex")
    for relative, parser in pages.items():
        for tag, attribute, raw_url, line in parser.references:
            if tag == "a" and attribute == "href" and raw_url:
                resolved = resolve_local(ROOT / relative, raw_url)
                if resolved is not None and resolved[0] == ROOT / "index.html":
                    if urlsplit(raw_url).path.endswith("index.html"):
                        errors.append(f"{relative}:{line}: link to the canonical homepage / instead of index.html")
    if f"Sitemap: {SITE_URL}sitemap.xml" not in (ROOT / "robots.txt").read_text(encoding="utf-8"):
        errors.append("robots.txt: expected the HTTPS sitemap URL")
    return errors


def check_insecure_urls() -> list[str]:
    errors: list[str] = []
    for extension in ("*.html", "*.css"):
        for path in sorted(ROOT.rglob(extension)):
            source = path.read_text(encoding="utf-8", errors="replace")
            for line_number, line in enumerate(source.splitlines(), start=1):
                if "http://" in line:
                    relative = path.relative_to(ROOT).as_posix()
                    errors.append(f"{relative}:{line_number}: insecure http:// URL")
    return errors


def check_tex_sources() -> list[str]:
    errors: list[str] = []
    graphic_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
    for path in sorted(ROOT.rglob("*.tex")):
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")
        for line_number, original_line in enumerate(source.splitlines(), start=1):
            line = re.split(r"(?<!\\)%", original_line, maxsplit=1)[0]
            if "http://" in line:
                errors.append(f"{relative}:{line_number}: insecure http:// URL")
            for match in TEX_GRAPHIC.finditer(line):
                raw_target = match.group(1)
                target = (path.parent / raw_target).resolve()
                candidates = [target] if target.suffix else [target.with_suffix(ext) for ext in graphic_extensions]
                if not any(candidate.exists() for candidate in candidates):
                    errors.append(f"{relative}:{line_number}: missing LaTeX graphic: {raw_target}")
    return errors


def main() -> int:
    pages, errors = parse_pages()
    errors.extend(check_references(pages))
    errors.extend(check_public_pages(pages))
    errors.extend(check_sitemap(pages))
    errors.extend(check_stylesheets())
    errors.extend(check_insecure_urls())
    errors.extend(check_tex_sources())

    if errors:
        print(f"Site check failed with {len(errors)} problem(s):")
        for error in sorted(set(errors)):
            print(f"  - {error}")
        return 1

    asset_count = sum(1 for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.relative_to(ROOT).parts)
    print(f"Site check passed: {len(pages)} HTML pages and {asset_count} total files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
