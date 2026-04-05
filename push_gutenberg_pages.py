#!/usr/bin/env python3
"""
Push Gutenberg-wrapped page content to hemle.blog.

Strips <style>, <html>, <head>, <body> from each template,
wraps the body content in <!-- wp:html --> blocks, and pushes
via WordPress.com API v1.1.

This prevents wpautop from mangling our HTML.

Usage:
    py -3.13 push_gutenberg_pages.py              # Push all 3 pages
    py -3.13 push_gutenberg_pages.py --page home   # Push one page
    py -3.13 push_gutenberg_pages.py --dry-run     # Preview locally
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.apis.wordpress import WordPressClient
from src.utils.logger import get_logger

log = get_logger("push-gutenberg")

TEMPLATES_DIR = Path(__file__).parent / "templates" / "wp_pages"

# Page definitions: key -> (template file, WP page ID, title)
PAGES = {
    "home": {
        "file": "home_forest_wp.html",
        "page_id": 13,
        "title": "Accueil",
    },
    "about": {
        "file": "about.html",
        "page_id": 15,
        "title": "À propos",
    },
    "subscribe": {
        "file": "subscribe.html",
        "page_id": 12,
        "title": "S'abonner",
    },
}


def extract_body(html: str) -> str:
    """
    Strip <style>, <!DOCTYPE>, <html>, <head>, <body> tags.
    Return only the inner content suitable for WordPress.
    """
    # Remove <!DOCTYPE ...>
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.IGNORECASE)

    # Remove <html ...> and </html>
    html = re.sub(r'</?html[^>]*>', '', html, flags=re.IGNORECASE)

    # Remove entire <head>...</head>
    html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.IGNORECASE | re.DOTALL)

    # Remove <body ...> and </body>
    html = re.sub(r'</?body[^>]*>', '', html, flags=re.IGNORECASE)

    # Remove <style>...</style> blocks (styles are in Additional CSS)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)

    # Remove HTML comments that aren't Gutenberg block markers
    html = re.sub(r'<!--(?!\s*/?wp:)[^>]*-->', '', html)

    # Clean up excessive blank lines
    html = re.sub(r'\n{3,}', '\n\n', html)

    return html.strip()


def wrap_gutenberg(body_html: str) -> str:
    """Wrap HTML content in a Gutenberg HTML block."""
    return f"<!-- wp:html -->\n{body_html}\n<!-- /wp:html -->"


async def push_page(wp: WordPressClient, key: str, dry_run: bool = False) -> bool:
    """Process and push a single page."""
    page_def = PAGES[key]
    template_path = TEMPLATES_DIR / page_def["file"]

    if not template_path.exists():
        print(f"  [{key}] SKIP — file not found: {template_path}")
        return False

    raw_html = template_path.read_text(encoding="utf-8")
    body = extract_body(raw_html)
    gutenberg = wrap_gutenberg(body)

    print(f"  [{key}] {page_def['title']} (ID={page_def['page_id']})")
    print(f"          Raw: {len(raw_html)} → Body: {len(body)} → Gutenberg: {len(gutenberg)} chars")

    if dry_run:
        # Save preview locally
        preview_path = Path(__file__).parent / "output" / "reports" / f"gutenberg_{key}.html"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(gutenberg, encoding="utf-8")
        print(f"          DRY RUN → saved to {preview_path}")
        return True

    try:
        result = await wp.update_post(page_def["page_id"], content=gutenberg)
        print(f"          OK — pushed to {result.get('link', result.get('URL', '???'))}")
        log.info(f"Gutenberg page pushed: {key} (ID={page_def['page_id']})")
        return True
    except Exception as e:
        print(f"          ERROR — {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Push Gutenberg-wrapped pages to hemle.blog")
    parser.add_argument("--page", choices=list(PAGES.keys()), default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    wp = WordPressClient()
    if not wp.token:
        print("  No WordPress.com token found.")
        return

    print(f"\n  Gutenberg Page Push — hemle.blog")
    print(f"  {'=' * 38}\n")

    pages_to_push = [args.page] if args.page else list(PAGES.keys())
    ok = 0

    for key in pages_to_push:
        if await push_page(wp, key, dry_run=args.dry_run):
            ok += 1

    print(f"\n  {'=' * 38}")
    action = "previewed" if args.dry_run else "pushed"
    print(f"  Done. {ok}/{len(pages_to_push)} pages {action}.\n")


if __name__ == "__main__":
    asyncio.run(main())
