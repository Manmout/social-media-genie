#!/usr/bin/env python3
"""
Regenerate the /rapports/ archive page from live posts.

Fetches all published posts from hemle.blog, builds cards from their
metadata, injects them into rapports.html template, and pushes the
result to the archive page via WordPress.com API v1.1.

Usage:
    py -3.13 update_archive.py              # Regenerate and publish
    py -3.13 update_archive.py --dry-run    # Preview locally only
    py -3.13 update_archive.py --status draft
"""

import argparse
import asyncio
import html as html_mod
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.apis.wordpress import WordPressClient
from src.utils.logger import get_logger

log = get_logger("update-archive")

TEMPLATE_PATH = Path(__file__).parent / "templates" / "wp_pages" / "rapports.html"
ARCHIVE_SLUG = "rapports"
ARCHIVE_TITLE = "Rapports"

# SVG arrow for card links (same as homepage)
SVG_ARROW = (
    '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;'
    'vertical-align:middle;margin-left:4px;">'
    '<path d="M2 10L10 2M10 2H4M10 2V8" stroke="currentColor" '
    'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

# French month names
MONTHS_FR = {
    1: "jan.", 2: "fév.", 3: "mars", 4: "avr.", 5: "mai", 6: "juin",
    7: "juil.", 8: "août", 9: "sept.", 10: "oct.", 11: "nov.", 12: "déc.",
}


def format_date_fr(iso_date: str) -> str:
    """Convert ISO date to French short format: '29 mars 2026'."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return f"{dt.day} {MONTHS_FR[dt.month]} {dt.year}"
    except Exception:
        return iso_date[:10]


def estimate_reading_time(content: str) -> int:
    """Estimate reading time in minutes from HTML content."""
    import re
    text = re.sub(r"<[^>]+>", "", content)
    words = len(text.split())
    return max(1, round(words / 200))


def build_card(post: dict) -> str:
    """Build a single archive card from a WP post dict."""
    title = html_mod.escape(post.get("title", ""))
    url = post.get("URL", post.get("url", "#"))
    date_str = format_date_fr(post.get("date", ""))
    excerpt = post.get("excerpt", "")

    # Clean excerpt (WP returns HTML with <p> tags)
    import re
    excerpt = re.sub(r"<[^>]+>", "", excerpt).strip()
    if len(excerpt) > 200:
        excerpt = excerpt[:197] + "..."
    excerpt = html_mod.escape(excerpt)

    # Extract category
    cats = post.get("categories", {})
    cat_name = "Trend Intelligence"
    for name in cats:
        if name not in ("Uncategorized",):
            cat_name = name
            break

    reading_min = estimate_reading_time(post.get("content", ""))

    return (
        f'<div class="rp-card">\n'
        f'  <div class="rp-card-meta">{date_str} &mdash; {html_mod.escape(cat_name)} &middot; {reading_min} min</div>\n'
        f'  <h2>{title}</h2>\n'
        f'  <p>{excerpt}</p>\n'
        f'  <a class="rp-card-link" href="{url}">Analyse compl&egrave;te{SVG_ARROW}</a>\n'
        f'</div>'
    )


async def find_page_by_slug(wp: WordPressClient, slug: str) -> dict | None:
    """Find an existing page by slug."""
    pages = await wp.list_posts(number=50, post_type="page")
    for p in pages:
        if slug in p.get("link", "") or slug in p.get("url", ""):
            return p
    return None


async def main():
    parser = argparse.ArgumentParser(description="Regenerate /rapports/ archive page")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", choices=["publish", "draft"], default="publish")
    args = parser.parse_args()

    wp = WordPressClient()
    if not wp.token:
        print("  No WordPress.com token found.")
        return

    print(f"\n  Trend Signal — Archive Page Generator")
    print(f"  {'=' * 42}\n")

    # 1. Fetch all published posts
    print("  Fetching published posts...", end=" ", flush=True)
    posts = await wp.list_posts(number=100, post_type="post")
    print(f"{len(posts)} found")

    if not posts:
        print("  No posts found. Nothing to do.")
        return

    # 2. Fetch full content for each post (for reading time + excerpt)
    import httpx
    full_posts = []
    headers = {"Authorization": f"Bearer {wp.token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        for p in posts:
            r = await client.get(
                f"https://public-api.wordpress.com/rest/v1.1/sites/{wp.site_id}/posts/{p['id']}",
                headers=headers,
            )
            if r.status_code == 200:
                full_posts.append(r.json())
            else:
                log.warning(f"Could not fetch post {p['id']}: {r.status_code}")

    # Sort by date descending
    full_posts.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 3. Build cards
    print(f"  Building {len(full_posts)} cards...")
    cards_html = "\n".join(build_card(p) for p in full_posts)

    # 4. Inject into template
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    page_html = template.replace("{{REPORT_CARDS}}", cards_html)

    # 5. Save locally
    local_path = Path(__file__).parent / "output" / "reports" / "archive_rapports.html"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(page_html, encoding="utf-8")
    print(f"  Saved locally: {local_path}")

    if args.dry_run:
        print(f"\n  DRY RUN — not publishing. Open {local_path} to preview.")
        return

    # 6. Publish or update
    existing = await find_page_by_slug(wp, ARCHIVE_SLUG)
    if existing:
        page_id = existing["id"]
        print(f"  Updating existing page ID={page_id}...", end=" ", flush=True)
        result = await wp.update_post(page_id, content=page_html)
        print("OK")
    else:
        print(f"  Creating new page '{ARCHIVE_TITLE}'...", end=" ", flush=True)
        result = await wp.create_post(
            title=ARCHIVE_TITLE,
            content=page_html,
            status=args.status,
            slug=ARCHIVE_SLUG,
            post_type="page",
        )
        print(f"OK → ID={result['id']}")

    print(f"\n  {'=' * 42}")
    print(f"  Archive live at: https://hemle.blog/{ARCHIVE_SLUG}/\n")


if __name__ == "__main__":
    asyncio.run(main())
